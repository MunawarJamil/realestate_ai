import logging
import uuid
from dataclasses import dataclass

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

    async def search(
        self, *, tenant_id: uuid.UUID, query: str, limit: int | None = None
    ) -> list[RetrievedChunk]:
        text = query.strip()
        if not text:
            raise InvalidQueryError("Search query must not be empty.")

        try:
            vector = await self._embedder.embed_query(text)
            scored = await self._store.search(
                tenant_id=tenant_id,
                vector=vector,
                limit=limit or self._default_limit,
                score_threshold=self._score_threshold,
            )
        except (EmbeddingError, UnexpectedResponse, ResponseHandlingException) as exc:
            logger.error("Retrieval failed for tenant %s: %r", tenant_id, exc)
            raise RetrievalUnavailableError("Search is temporarily unavailable.") from exc

        if not scored:
            return []

        # Vector search does not know document state. Only READY documents may be returned, which
        # also hides half-ingested documents and any vectors that outlived their document.
        documents = await self._repository.get_ready_by_ids(
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