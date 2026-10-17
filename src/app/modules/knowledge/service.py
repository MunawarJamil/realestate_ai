import asyncio
import hashlib
import logging
import uuid
from pathlib import PurePosixPath
from typing import Protocol

from app.modules.knowledge.content_types import (
    ensure_content_matches_type,
    resolve_content_type,
    sanitize_filename,
)
from app.modules.knowledge.enums import DocumentStatus
from app.modules.knowledge.exceptions import (
    DocumentNotFoundError,
    DuplicateDocumentError,
    FileTooLargeError,
    InvalidDocumentError,
    QueueUnavailableError,
)
from app.modules.knowledge.models import KnowledgeDocument
from app.modules.knowledge.repository import KnowledgeDocumentRepository
from app.modules.knowledge.storage import FileStorage, build_storage_key
from app.modules.knowledge.vector_store import ChunkVectorStore

logger = logging.getLogger(__name__)

_MAX_TITLE_LENGTH = 255


class IngestionQueue(Protocol):
    async def enqueue(self, *, tenant_id: uuid.UUID, document_id: uuid.UUID) -> None: ...


class KnowledgeService:
    """Upload, list, inspect and delete knowledge documents for a tenant."""

    def __init__(
        self,
        *,
        repository: KnowledgeDocumentRepository,
        storage: FileStorage,
        store: ChunkVectorStore,
        queue: IngestionQueue,
        max_upload_bytes: int,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._store = store
        self._queue = queue
        self._max_upload_bytes = max_upload_bytes

    async def upload(
        self,
        *,
        tenant_id: uuid.UUID,
        filename: str | None,
        declared_content_type: str | None,
        data: bytes,
        title: str | None = None,
    ) -> KnowledgeDocument:
        if not data:
            raise InvalidDocumentError("The uploaded file is empty.")
        if len(data) > self._max_upload_bytes:
            raise FileTooLargeError(self._max_upload_bytes)

        safe_name = sanitize_filename(filename)
        content_type = resolve_content_type(safe_name, declared_content_type)
        ensure_content_matches_type(content_type, data)

        checksum = await asyncio.to_thread(lambda: hashlib.sha256(data).hexdigest())
        existing = await self._repository.get_by_checksum(tenant_id=tenant_id, checksum=checksum)
        if existing is not None:
            raise DuplicateDocumentError(existing.id)

        document_id = uuid.uuid7()
        storage_key = build_storage_key(tenant_id, document_id)
        document = KnowledgeDocument(
            id=document_id,
            tenant_id=tenant_id,
            title=_resolve_title(title, safe_name),
            original_filename=safe_name,
            content_type=content_type,
            size_bytes=len(data),
            checksum_sha256=checksum,
            storage_key=storage_key,
        )

        # File first: the worker must be able to read it the moment the row becomes visible.
        await self._storage.save(key=storage_key, data=data)
        try:
            created = await self._repository.add(document)
            if created is None:  # lost a race against a concurrent identical upload
                winner = await self._repository.get_by_checksum(
                    tenant_id=tenant_id, checksum=checksum
                )
                raise DuplicateDocumentError(winner.id if winner else None)
            # Commit BEFORE enqueueing, otherwise the worker can look for a row that is not
            # visible yet and silently skip the job.
            await self._repository.commit()
        except BaseException:  # also clean up on cancellation
            await self._discard_file(storage_key)
            raise

        try:
            await self._queue.enqueue(tenant_id=tenant_id, document_id=document_id)
        except QueueUnavailableError:
            await self._roll_back_upload(tenant_id, document_id, storage_key)
            raise
        return created

    async def get(self, *, tenant_id: uuid.UUID, document_id: uuid.UUID) -> KnowledgeDocument:
        document = await self._repository.get(tenant_id=tenant_id, document_id=document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)
        return document

    async def list_documents(
        self,
        *,
        tenant_id: uuid.UUID,
        status: DocumentStatus | None,
        limit: int,
        offset: int,
    ) -> tuple[list[KnowledgeDocument], int]:
        items = await self._repository.list_for_tenant(
            tenant_id=tenant_id, status=status, limit=limit, offset=offset
        )
        total = await self._repository.count_for_tenant(tenant_id=tenant_id, status=status)
        return items, total

    async def delete(self, *, tenant_id: uuid.UUID, document_id: uuid.UUID) -> None:
        document = await self.get(tenant_id=tenant_id, document_id=document_id)
        storage_key = document.storage_key

        # Vectors first: vector search does not consult Postgres, so leftover vectors would keep
        # a deleted document searchable. A retry after a partial failure is safe (idempotent).
        await self._store.delete_document(tenant_id=tenant_id, document_id=document_id)
        await self._repository.delete(tenant_id=tenant_id, document_id=document_id)
        await self._repository.commit()
        await self._discard_file(storage_key)

    async def _roll_back_upload(
        self, tenant_id: uuid.UUID, document_id: uuid.UUID, storage_key: str
    ) -> None:
        """Queue is down: remove the row and file so the client can simply retry the upload."""
        try:
            await self._repository.delete(tenant_id=tenant_id, document_id=document_id)
            await self._repository.commit()
        except Exception:
            logger.exception("Could not roll back document %s after queue failure", document_id)
        await self._discard_file(storage_key)

    async def _discard_file(self, storage_key: str) -> None:
        try:
            await self._storage.delete(storage_key)
        except Exception:
            logger.exception("Could not delete stored file %s", storage_key)


def _resolve_title(title: str | None, filename: str) -> str:
    candidate = (title or "").strip() or PurePosixPath(filename).stem or filename
    return candidate[:_MAX_TITLE_LENGTH]