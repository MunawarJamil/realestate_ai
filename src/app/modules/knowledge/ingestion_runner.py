import logging
import uuid
from typing import Final

from app.integrations.embeddings.exceptions import EmbeddingDimensionError
from app.modules.knowledge.exceptions import KnowledgeError
from app.modules.knowledge.ingestion import IngestionPipeline
from app.modules.knowledge.repository import RepositoryScope
from app.modules.knowledge.storage import FileStorage
from app.modules.knowledge.vector_store import ChunkVectorStore

logger = logging.getLogger(__name__)

# Retrying cannot fix these: the data or the configuration is the problem.
_PERMANENT_ERRORS: Final = (KnowledgeError, EmbeddingDimensionError)
FINAL_FAILURE_MESSAGE: Final = "Processing failed after several attempts. Please try again later."


class TransientIngestionError(Exception):
    """The attempt failed for a reason that may go away; the job should be retried."""


class IngestionRunner:
    """Runs one ingestion attempt and owns the document's status transitions.

    Transport-agnostic on purpose: the ARQ task only translates TransientIngestionError into a
    retry. Error text shown to tenants is limited to our own domain messages; anything else is
    logged and replaced by a generic message.
    """

    def __init__(
        self,
        *,
        repository_scope: RepositoryScope,
        storage: FileStorage,
        pipeline: IngestionPipeline,
        store: ChunkVectorStore,
    ) -> None:
        self._repository_scope = repository_scope
        self._storage = storage
        self._pipeline = pipeline
        self._store = store

    async def run(
        self,
        *,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        attempt: int,
        max_attempts: int,
    ) -> None:
        async with self._repository_scope() as repository:
            document = await repository.claim_for_processing(
                tenant_id=tenant_id, document_id=document_id
            )
        if document is None:
            logger.info("Skipping document %s: missing or already processed", document_id)
            return
        storage_key, content_type = document.storage_key, document.content_type

        try:
            data = await self._storage.read(storage_key)
            result = await self._pipeline.ingest(
                tenant_id=tenant_id,
                document_id=document_id,
                content_type=content_type,
                data=data,
            )
        except _PERMANENT_ERRORS as exc:
            logger.warning("Document %s cannot be ingested: %s", document_id, exc)
            await self._fail(tenant_id, document_id, str(exc))
            return
        except Exception as exc:
            if attempt < max_attempts:
                logger.warning(
                    "Ingestion attempt %d/%d failed for document %s: %r",
                    attempt, max_attempts, document_id, exc,
                )
                raise TransientIngestionError(str(exc)) from exc
            logger.exception(
                "Ingestion failed for document %s after %d attempts", document_id, attempt
            )
            await self._fail(tenant_id, document_id, FINAL_FAILURE_MESSAGE)
            return

        async with self._repository_scope() as repository:
            updated = await repository.mark_ready(
                tenant_id=tenant_id, document_id=document_id, chunk_count=result.chunk_count
            )
        if not updated:
            logger.info("Document %s was deleted during ingestion; removing vectors", document_id)
            await self._discard_vectors(tenant_id, document_id)

    async def _fail(self, tenant_id: uuid.UUID, document_id: uuid.UUID, message: str) -> None:
        await self._discard_vectors(tenant_id, document_id)
        async with self._repository_scope() as repository:
            await repository.mark_failed(
                tenant_id=tenant_id, document_id=document_id, error_message=message
            )

    async def _discard_vectors(self, tenant_id: uuid.UUID, document_id: uuid.UUID) -> None:
        """Best effort: a failed cleanup must never hide the original outcome."""
        try:
            await self._store.delete_document(tenant_id=tenant_id, document_id=document_id)
        except Exception:
            logger.exception("Could not remove vectors for document %s", document_id)