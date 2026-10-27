import logging
import uuid
from dataclasses import dataclass
from typing import Any

from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langsmith import traceable
from pydantic import Field
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from app.integrations.embeddings.base import EmbeddingProvider
from app.integrations.embeddings.exceptions import EmbeddingError
from app.modules.knowledge.exceptions import InvalidQueryError, RetrievalUnavailableError
from app.modules.knowledge.repository import KnowledgeDocumentRepository
from app.modules.knowledge.vector_store import ChunkVectorStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    document_id: uuid.UUID
    document_title: str
    page_number: int
    chunk_index: int
    text: str
    score: float


def _format_retriever_output(output: Any) -> dict[str, Any]:
    """Render chunks in LangSmith's native retriever 'Documents' view."""
    chunks = output if isinstance(output, list) else output.get("output", [])
    return {
        "documents": [
            {
                "page_content": c.text,
                "type": "Document",
                "metadata": {
                    "document_id": str(c.document_id),
                    "title": c.document_title,
                    "page": c.page_number,
                    "chunk_index": c.chunk_index,
                    "score": round(c.score, 4),
                },
            }
            for c in chunks
        ]
    }


@traceable(
    run_type="retriever",
    name="qdrant_retrieval",
    process_outputs=_format_retriever_output,
)
async def _traced_search(
    *,
    embedder: EmbeddingProvider,
    store: ChunkVectorStore,
    repository: KnowledgeDocumentRepository,
    tenant_id: uuid.UUID,
    query: str,
    limit: int,
    score_threshold: float | None = None,
) -> list[RetrievedChunk]:
    text = query.strip()
    if not text:
        raise InvalidQueryError("Search query must not be empty.")

    try:
        vector = await embedder.embed_query(text)
        scored = await store.hybrid_search(
            tenant_id=tenant_id,
            vector=vector,
            query_text=text,
            limit=limit,
            score_threshold=score_threshold,
        )

    except (EmbeddingError, UnexpectedResponse, ResponseHandlingException) as exc:
        logger.error("Retrieval failed for tenant %s: %r", tenant_id, exc)
        raise RetrievalUnavailableError("Search is temporarily unavailable.") from exc

    if not scored:
        return []

    # Vector search does not know document state. Only READY documents may be returned, which
    # also hides half-ingested documents and any vectors that outlived their document.
    documents = await repository.get_ready_by_ids(
        tenant_id=tenant_id, document_ids={chunk.document_id for chunk in scored}
    )
    return [
        RetrievedChunk(
            document_id=chunk.document_id,
            document_title=documents[chunk.document_id].title,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            score=chunk.score,
        )
        for chunk in scored
        if chunk.document_id in documents
    ]




class TenantAwareRetriever(BaseRetriever):
    """LangChain-compatible retriever strictly scoped to a single tenant."""
    service: RetrievalService = Field(exclude=True)
    tenant_id: uuid.UUID
    limit: int = 5
    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        raise NotImplementedError("Use async retrieval with ainvoke().")


    async def _aget_relevant_documents(
        self, query: str, *, run_manager: AsyncCallbackManagerForRetrieverRun
    ) -> list[Document]:
        chunks = await self.service.search(
            tenant_id=self.tenant_id,
            query=query,
            limit=self.limit,
        )
        return [
            Document(
                page_content=c.text,
                metadata={
                    "document_id": str(c.document_id),
                    "document_title": c.document_title,
                    "page_number": c.page_number,
                    "chunk_index": c.chunk_index,
                    "score": c.score,
                },
            )
            for c in chunks
        ]


class RetrievalService:
    """Semantic search over one tenant's knowledge base."""

    def __init__(
        self,
        *,
        embedder: EmbeddingProvider,
        store: ChunkVectorStore,
        repository: KnowledgeDocumentRepository,
        default_limit: int,
        score_threshold: float | None = None,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._repository = repository
        self._default_limit = default_limit
        self._score_threshold = score_threshold


 
    def as_langchain_retriever(
        self, tenant_id: uuid.UUID, limit: int | None = None
    ) -> TenantAwareRetriever:
        """Returns a LangChain-native BaseRetriever bound to this specific tenant."""
        return TenantAwareRetriever(
            service=self,
            tenant_id=tenant_id,
            limit=limit or self._default_limit,
        )

    async def search(
        self, *, tenant_id: uuid.UUID, query: str, limit: int | None = None
    ) -> list[RetrievedChunk]:
        return await _traced_search(
            embedder=self._embedder,
            store=self._store,
            repository=self._repository,
            tenant_id=tenant_id,
            query=query,
            limit=limit or self._default_limit,
            score_threshold=self._score_threshold,
        )

