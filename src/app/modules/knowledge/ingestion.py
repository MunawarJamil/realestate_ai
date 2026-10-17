import asyncio
import logging
import uuid
from dataclasses import dataclass

from app.core.config import get_settings
from app.integrations.embeddings.base import EmbeddingProvider
from app.integrations.embeddings.client import get_embedding_client
from app.integrations.qdrant.client import get_qdrant
from app.modules.knowledge.chunking import TextChunker
from app.modules.knowledge.exceptions import DocumentTooLargeError
from app.modules.knowledge.extractors import extract_pages
from app.modules.knowledge.vector_store import ChunkVectorStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IngestionResult:
    page_count: int
    chunk_count: int


class IngestionPipeline:
    """extract -> chunk -> embed -> upsert. Idempotent: safe to re-run for the same document.

    Chunks are embedded and written in bounded windows, so memory stays flat for large files.
    Status tracking, retries and cleanup on final failure belong to the caller (the worker).
    """

    def __init__(
        self,
        *,
        embedder: EmbeddingProvider,
        store: ChunkVectorStore,
        chunker: TextChunker,
        max_chunks: int,
        batch_size: int = 64,
    ) -> None:
        if max_chunks <= 0 or batch_size <= 0:
            raise ValueError("max_chunks and batch_size must be positive.")
        self._embedder = embedder
        self._store = store
        self._chunker = chunker
        self._max_chunks = max_chunks
        self._batch_size = batch_size

    async def ingest(
        self,
        *,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        content_type: str,
        data: bytes,
    ) -> IngestionResult:
        pages = await extract_pages(content_type, data)
        chunks = await asyncio.to_thread(self._chunker.chunk_pages, pages)

        # Reject before spending any embedding quota.
        if len(chunks) > self._max_chunks:
            raise DocumentTooLargeError(len(chunks), self._max_chunks)

        for start in range(0, len(chunks), self._batch_size):
            window = chunks[start : start + self._batch_size]
            vectors = await self._embedder.embed_documents([chunk.text for chunk in window])
            await self._store.upsert_chunks(
                tenant_id=tenant_id, document_id=document_id, chunks=window, vectors=vectors
            )

        await self._store.delete_stale_chunks(
            tenant_id=tenant_id, document_id=document_id, keep_count=len(chunks)
        )

        logger.info(
            "Ingested document %s for tenant %s: %d pages, %d chunks",
            document_id, tenant_id, len(pages), len(chunks),
        )
        return IngestionResult(page_count=len(pages), chunk_count=len(chunks))


def build_ingestion_pipeline() -> IngestionPipeline:
    """Wire the pipeline from process-wide clients (API process and ARQ worker both use this)."""
    settings = get_settings()
    return IngestionPipeline(
        embedder=get_embedding_client(),
        store=ChunkVectorStore(get_qdrant(), settings.qdrant_collection),
        chunker=TextChunker(settings.chunk_size_chars, settings.chunk_overlap_chars),
        max_chunks=settings.max_chunks_per_document,
        batch_size=settings.ingestion_batch_size,
    )