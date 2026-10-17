import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest

from app.integrations.embeddings.exceptions import EmbeddingDimensionError, EmbeddingError
from app.modules.knowledge.exceptions import (
    DocumentTooLargeError,
    EmptyDocumentError,
    ExtractionError,
    StorageFileNotFoundError,
    UnsupportedContentTypeError,
)
from app.modules.knowledge.ingestion import IngestionPipeline, IngestionResult
from app.modules.knowledge.ingestion_runner import (
    FINAL_FAILURE_MESSAGE,
    IngestionRunner,
    TransientIngestionError,
)
from app.modules.knowledge.repository import KnowledgeDocumentRepository
from app.modules.knowledge.vector_store import ChunkVectorStore

TENANT_ID = uuid.uuid4()
DOCUMENT_ID = uuid.uuid4()
CONTENT = b"brochure bytes"


class FakeStorage:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.read_keys: list[str] = []

    async def save(self, *, key: str, data: bytes) -> None:
        raise NotImplementedError

    async def read(self, key: str) -> bytes:
        self.read_keys.append(key)
        if self.error is not None:
            raise self.error
        return CONTENT

    async def delete(self, key: str) -> None:
        raise NotImplementedError


@pytest.fixture
def repository() -> KnowledgeDocumentRepository:
    repo: KnowledgeDocumentRepository = create_autospec(KnowledgeDocumentRepository, instance=True)
    repo.claim_for_processing.return_value = SimpleNamespace(  # type: ignore[attr-defined]
        storage_key="tenant/doc", content_type="application/pdf"
    )
    repo.mark_ready.return_value = True  # type: ignore[attr-defined]
    repo.mark_failed.return_value = True  # type: ignore[attr-defined]
    return repo


@pytest.fixture
def pipeline() -> IngestionPipeline:
    mock: IngestionPipeline = create_autospec(IngestionPipeline, instance=True)
    mock.ingest.return_value = IngestionResult(page_count=2, chunk_count=7)  # type: ignore[attr-defined]
    return mock


@pytest.fixture
def store() -> ChunkVectorStore:
    mock: ChunkVectorStore = create_autospec(ChunkVectorStore, instance=True)
    return mock


def make_runner(
    repository: KnowledgeDocumentRepository,
    pipeline: IngestionPipeline,
    store: ChunkVectorStore,
    storage: FakeStorage | None = None,
) -> IngestionRunner:
    @asynccontextmanager
    async def scope() -> AsyncIterator[KnowledgeDocumentRepository]:
        yield repository

    return IngestionRunner(
        repository_scope=scope,
        storage=storage or FakeStorage(),
        pipeline=pipeline,
        store=store,
    )


async def run(runner: IngestionRunner, *, attempt: int = 1, max_attempts: int = 3) -> None:
    await runner.run(
        tenant_id=TENANT_ID, document_id=DOCUMENT_ID, attempt=attempt, max_attempts=max_attempts
    )


async def test_success_marks_document_ready_with_chunk_count(
    repository: KnowledgeDocumentRepository, pipeline: IngestionPipeline, store: ChunkVectorStore
) -> None:
    storage = FakeStorage()

    await run(make_runner(repository, pipeline, store, storage))

    assert storage.read_keys == ["tenant/doc"]
    pipeline.ingest.assert_awaited_once_with(  # type: ignore[attr-defined]
        tenant_id=TENANT_ID,
        document_id=DOCUMENT_ID,
        content_type="application/pdf",
        data=CONTENT,
    )
    repository.mark_ready.assert_awaited_once_with(  # type: ignore[attr-defined]
        tenant_id=TENANT_ID, document_id=DOCUMENT_ID, chunk_count=7
    )
    repository.mark_failed.assert_not_awaited()  # type: ignore[attr-defined]
    store.delete_document.assert_not_awaited()  # type: ignore[attr-defined]


async def test_unclaimable_document_is_skipped(
    repository: KnowledgeDocumentRepository, pipeline: IngestionPipeline, store: ChunkVectorStore
) -> None:
    repository.claim_for_processing.return_value = None  # type: ignore[attr-defined]
    storage = FakeStorage()

    await run(make_runner(repository, pipeline, store, storage))

    assert storage.read_keys == []
    pipeline.ingest.assert_not_awaited()  # type: ignore[attr-defined]
    repository.mark_ready.assert_not_awaited()  # type: ignore[attr-defined]
    repository.mark_failed.assert_not_awaited()  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "error",
    [
        ExtractionError("PDF could not be read."),
        UnsupportedContentTypeError("image/png"),
        EmptyDocumentError("no text"),
        DocumentTooLargeError(5, 2),
        EmbeddingDimensionError("wrong size"),
    ],
)
async def test_permanent_error_fails_immediately_without_retry(
    repository: KnowledgeDocumentRepository,
    pipeline: IngestionPipeline,
    store: ChunkVectorStore,
    error: Exception,
) -> None:
    pipeline.ingest.side_effect = error  # type: ignore[attr-defined]

    await run(make_runner(repository, pipeline, store), attempt=1, max_attempts=3)

    repository.mark_failed.assert_awaited_once_with(  # type: ignore[attr-defined]
        tenant_id=TENANT_ID, document_id=DOCUMENT_ID, error_message=str(error)
    )
    store.delete_document.assert_awaited_once_with(  # type: ignore[attr-defined]
        tenant_id=TENANT_ID, document_id=DOCUMENT_ID
    )
    repository.mark_ready.assert_not_awaited()  # type: ignore[attr-defined]


async def test_missing_stored_file_is_a_permanent_failure(
    repository: KnowledgeDocumentRepository, pipeline: IngestionPipeline, store: ChunkVectorStore
) -> None:
    storage = FakeStorage(error=StorageFileNotFoundError("tenant/doc"))

    await run(make_runner(repository, pipeline, store, storage))

    repository.mark_failed.assert_awaited_once()  # type: ignore[attr-defined]
    pipeline.ingest.assert_not_awaited()  # type: ignore[attr-defined]


async def test_transient_error_requests_retry_and_leaves_state_untouched(
    repository: KnowledgeDocumentRepository, pipeline: IngestionPipeline, store: ChunkVectorStore
) -> None:
    pipeline.ingest.side_effect = EmbeddingError("provider down")  # type: ignore[attr-defined]

    with pytest.raises(TransientIngestionError):
        await run(make_runner(repository, pipeline, store), attempt=1, max_attempts=3)

    repository.mark_failed.assert_not_awaited()  # type: ignore[attr-defined]
    repository.mark_ready.assert_not_awaited()  # type: ignore[attr-defined]
    store.delete_document.assert_not_awaited()  # type: ignore[attr-defined]


async def test_transient_error_on_last_attempt_fails_with_generic_message(
    repository: KnowledgeDocumentRepository, pipeline: IngestionPipeline, store: ChunkVectorStore
) -> None:
    pipeline.ingest.side_effect = EmbeddingError("secret provider detail")  # type: ignore[attr-defined]

    await run(make_runner(repository, pipeline, store), attempt=3, max_attempts=3)

    kwargs = repository.mark_failed.await_args.kwargs  # type: ignore[attr-defined]
    assert kwargs["error_message"] == FINAL_FAILURE_MESSAGE
    assert "secret" not in kwargs["error_message"]
    store.delete_document.assert_awaited_once()  # type: ignore[attr-defined]


async def test_document_deleted_during_ingestion_discards_vectors(
    repository: KnowledgeDocumentRepository, pipeline: IngestionPipeline, store: ChunkVectorStore
) -> None:
    repository.mark_ready.return_value = False  # type: ignore[attr-defined]

    await run(make_runner(repository, pipeline, store))

    store.delete_document.assert_awaited_once_with(  # type: ignore[attr-defined]
        tenant_id=TENANT_ID, document_id=DOCUMENT_ID
    )


async def test_vector_cleanup_failure_does_not_block_failed_status(
    repository: KnowledgeDocumentRepository, pipeline: IngestionPipeline, store: ChunkVectorStore
) -> None:
    pipeline.ingest.side_effect = ExtractionError("bad file")  # type: ignore[attr-defined]
    store.delete_document.side_effect = RuntimeError("qdrant down")  # type: ignore[attr-defined]

    await run(make_runner(repository, pipeline, store))

    repository.mark_failed.assert_awaited_once()  # type: ignore[attr-defined]