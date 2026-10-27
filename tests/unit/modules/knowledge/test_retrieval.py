import uuid
from collections.abc import Sequence
from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest
from qdrant_client.http.exceptions import ResponseHandlingException

from app.integrations.embeddings.exceptions import EmbeddingError
from app.modules.knowledge.exceptions import InvalidQueryError, RetrievalUnavailableError
from app.modules.knowledge.repository import KnowledgeDocumentRepository
from app.modules.knowledge.retrieval import RetrievalService
from app.modules.knowledge.vector_store import ChunkVectorStore, ScoredChunk

TENANT_ID = uuid.uuid4()
DEFAULT_LIMIT = 5
THRESHOLD = 0.25
QUERY_VECTOR = [0.1, 0.2, 0.3]


class FakeEmbedder:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.queries: list[str] = []

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError

    async def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        if self.error is not None:
            raise self.error
        return QUERY_VECTOR

    async def aclose(self) -> None:
        return None


def scored(document_id: uuid.UUID, index: int, score: float) -> ScoredChunk:
    return ScoredChunk(
        document_id=document_id, chunk_index=index, page_number=index + 1, text=f"t{index}", score=score
    )


@pytest.fixture
def store() -> ChunkVectorStore:
    mock: ChunkVectorStore = create_autospec(ChunkVectorStore, instance=True)
    mock.search.return_value = []  # type: ignore[attr-defined]
    mock.hybrid_search.return_value = []  # type: ignore[attr-defined]
    return mock



@pytest.fixture
def repository() -> KnowledgeDocumentRepository:
    mock: KnowledgeDocumentRepository = create_autospec(KnowledgeDocumentRepository, instance=True)
    mock.get_ready_by_ids.return_value = {}  # type: ignore[attr-defined]
    return mock


def make_service(
    embedder: FakeEmbedder,
    store: ChunkVectorStore,
    repository: KnowledgeDocumentRepository,
) -> RetrievalService:
    return RetrievalService(
        embedder=embedder,
        store=store,
        repository=repository,
        default_limit=DEFAULT_LIMIT,
        score_threshold=THRESHOLD,
    )


@pytest.mark.parametrize("query", ["", "   ", "\n\t"])
async def test_blank_query_is_rejected_without_embedding(
    store: ChunkVectorStore, repository: KnowledgeDocumentRepository, query: str
) -> None:
    embedder = FakeEmbedder()

    with pytest.raises(InvalidQueryError):
        await make_service(embedder, store, repository).search(tenant_id=TENANT_ID, query=query)

    assert embedder.queries == []


async def test_search_embeds_trimmed_query_and_scopes_by_tenant(
    store: ChunkVectorStore, repository: KnowledgeDocumentRepository
) -> None:
    embedder = FakeEmbedder()

    await make_service(embedder, store, repository).search(
        tenant_id=TENANT_ID, query="  3 bed villa  "
    )

    assert embedder.queries == ["3 bed villa"]
    store.hybrid_search.assert_awaited_once_with(  # type: ignore[attr-defined]
        tenant_id=TENANT_ID,
        vector=QUERY_VECTOR,
        query_text="3 bed villa",
        limit=DEFAULT_LIMIT,
        score_threshold=THRESHOLD,
    )


async def test_explicit_limit_overrides_default(
    store: ChunkVectorStore, repository: KnowledgeDocumentRepository
) -> None:
    await make_service(FakeEmbedder(), store, repository).search(
        tenant_id=TENANT_ID, query="villa", limit=2
    )

    assert store.hybrid_search.await_args.kwargs["limit"] == 2  # type: ignore[attr-defined]


async def test_no_matches_returns_empty_without_database_lookup(
    store: ChunkVectorStore, repository: KnowledgeDocumentRepository
) -> None:
    results = await make_service(FakeEmbedder(), store, repository).search(
        tenant_id=TENANT_ID, query="villa"
    )

    assert results == []
    repository.get_ready_by_ids.assert_not_awaited()  # type: ignore[attr-defined]


async def test_results_keep_score_order_and_carry_document_titles(
    store: ChunkVectorStore, repository: KnowledgeDocumentRepository
) -> None:
    doc_a, doc_b = uuid.uuid4(), uuid.uuid4()
    store.hybrid_search.return_value = [scored(doc_b, 0, 0.9), scored(doc_a, 4, 0.7)]  # type: ignore[attr-defined]
    repository.get_ready_by_ids.return_value = {  # type: ignore[attr-defined]
        doc_a: SimpleNamespace(title="Brochure A"),
        doc_b: SimpleNamespace(title="Brochure B"),
    }

    results = await make_service(FakeEmbedder(), store, repository).search(
        tenant_id=TENANT_ID, query="villa"
    )

    assert [(r.document_title, r.chunk_index, r.score) for r in results] == [
        ("Brochure B", 0, 0.9),
        ("Brochure A", 4, 0.7),
    ]
    lookup = repository.get_ready_by_ids.await_args.kwargs  # type: ignore[attr-defined]
    assert lookup["tenant_id"] == TENANT_ID
    assert lookup["document_ids"] == {doc_a, doc_b}


async def test_chunks_of_documents_that_are_not_ready_are_dropped(
    store: ChunkVectorStore, repository: KnowledgeDocumentRepository
) -> None:
    ready_doc, processing_or_deleted_doc = uuid.uuid4(), uuid.uuid4()
    store.hybrid_search.return_value = [  # type: ignore[attr-defined]
        scored(processing_or_deleted_doc, 0, 0.95),
        scored(ready_doc, 1, 0.80),
    ]
    repository.get_ready_by_ids.return_value = {  # type: ignore[attr-defined]
        ready_doc: SimpleNamespace(title="Ready doc")
    }

    results = await make_service(FakeEmbedder(), store, repository).search(
        tenant_id=TENANT_ID, query="villa"
    )

    assert [r.document_id for r in results] == [ready_doc]


async def test_embedding_failure_becomes_retrieval_unavailable(
    store: ChunkVectorStore, repository: KnowledgeDocumentRepository
) -> None:
    embedder = FakeEmbedder(error=EmbeddingError("provider down"))

    with pytest.raises(RetrievalUnavailableError):
        await make_service(embedder, store, repository).search(tenant_id=TENANT_ID, query="villa")

    store.hybrid_search.assert_not_awaited()  # type: ignore[attr-defined]


async def test_vector_store_failure_becomes_retrieval_unavailable(
    store: ChunkVectorStore, repository: KnowledgeDocumentRepository
) -> None:
    store.hybrid_search.side_effect = ResponseHandlingException(Exception("qdrant down"))  # type: ignore[attr-defined]

    with pytest.raises(RetrievalUnavailableError):
        await make_service(FakeEmbedder(), store, repository).search(
            tenant_id=TENANT_ID, query="villa"
        )