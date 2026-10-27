from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any, Final, cast 
from sqlalchemy import func, select, update , delete
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import IntegrityError
from app.modules.knowledge.enums import DocumentStatus
from app.modules.knowledge.models import KnowledgeDocument
from collections.abc import Collection
_MAX_ERROR_LENGTH: Final = 1000
# PROCESSING is claimable so a job that crashed mid-run (or is retried) can resume.
_CLAIMABLE: Final = (DocumentStatus.PENDING, DocumentStatus.PROCESSING, DocumentStatus.FAILED)


class KnowledgeDocumentRepository:
    """Pure DB access. Every query is tenant-scoped. Callers own commit/rollback."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, *, tenant_id: uuid.UUID, document_id: uuid.UUID
    ) -> KnowledgeDocument | None:
        stmt = select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.tenant_id == tenant_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def claim_for_processing(
        self, *, tenant_id: uuid.UUID, document_id: uuid.UUID
    ) -> KnowledgeDocument | None:
        """Atomically move a document to PROCESSING. Returns None if it is gone or already READY."""
        stmt = (
            update(KnowledgeDocument)
            .where(
                KnowledgeDocument.id == document_id,
                KnowledgeDocument.tenant_id == tenant_id,
                KnowledgeDocument.status.in_(_CLAIMABLE),
            )
            .values(status=DocumentStatus.PROCESSING, error_message=None)
            .returning(KnowledgeDocument)
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def mark_ready(
        self, *, tenant_id: uuid.UUID, document_id: uuid.UUID, chunk_count: int
    ) -> bool:
        return await self._apply(
            tenant_id,
            document_id,
            status=DocumentStatus.READY,
            chunk_count=chunk_count,
            processed_at=func.now(),
            error_message=None,
        )

    async def mark_failed(
        self, *, tenant_id: uuid.UUID, document_id: uuid.UUID, error_message: str
    ) -> bool:
        return await self._apply(
            tenant_id,
            document_id,
            status=DocumentStatus.FAILED,
            error_message=error_message[:_MAX_ERROR_LENGTH],
        )

    async def _apply(
        self, tenant_id: uuid.UUID, document_id: uuid.UUID, **values: Any
    ) -> bool:
        """Returns False when no row matched (e.g. the document was deleted mid-ingestion)."""
        stmt = (
            update(KnowledgeDocument)
            .where(
                KnowledgeDocument.id == document_id,
                KnowledgeDocument.tenant_id == tenant_id,
            )
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        result = cast("CursorResult[Any]", await self._session.execute(stmt))
        return result.rowcount > 0



    async def add(self, document: KnowledgeDocument) -> KnowledgeDocument | None:
        """Insert inside a savepoint. Returns None if (tenant_id, checksum) already exists."""
        try:
            async with self._session.begin_nested():
                self._session.add(document)
        except IntegrityError:
            return None
        # Load server-side defaults (created_at, updated_at); async sessions cannot lazy-load.
        await self._session.refresh(document)
        return document

    async def get_by_checksum(
        self, *, tenant_id: uuid.UUID, checksum: str
    ) -> KnowledgeDocument | None:
        stmt = select(KnowledgeDocument).where(
            KnowledgeDocument.tenant_id == tenant_id,
            KnowledgeDocument.checksum_sha256 == checksum,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_for_tenant(
        self,
        *,
        tenant_id: uuid.UUID,
        status: DocumentStatus | None,
        limit: int,
        offset: int,
    ) -> list[KnowledgeDocument]:
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.tenant_id == tenant_id)
            .order_by(KnowledgeDocument.created_at.desc(), KnowledgeDocument.id.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            stmt = stmt.where(KnowledgeDocument.status == status)
        return list((await self._session.execute(stmt)).scalars().all())

    async def count_for_tenant(self, *, tenant_id: uuid.UUID, status: DocumentStatus | None) -> int:
        stmt = (
            select(func.count())
            .select_from(KnowledgeDocument)
            .where(KnowledgeDocument.tenant_id == tenant_id)
        )
        if status is not None:
            stmt = stmt.where(KnowledgeDocument.status == status)
        return (await self._session.execute(stmt)).scalar_one()

    async def delete(self, *, tenant_id: uuid.UUID, document_id: uuid.UUID) -> bool:
        stmt = delete(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.tenant_id == tenant_id,
        )
        result = cast("CursorResult[Any]", await self._session.execute(stmt))
        return result.rowcount > 0

    async def commit(self) -> None:
        """Explicit commit, needed when a job must only be enqueued after the row is visible."""
        await self._session.commit()


    async def get_ready_by_ids(
        self, *, tenant_id: uuid.UUID, document_ids: Collection[uuid.UUID]
    ) -> dict[uuid.UUID, KnowledgeDocument]:
        if not document_ids:
            return {}
        stmt = select(KnowledgeDocument).where(
            KnowledgeDocument.tenant_id == tenant_id,
            KnowledgeDocument.id.in_(document_ids),
            KnowledgeDocument.status == DocumentStatus.READY,
        )
        rows = (await self._session.execute(stmt)).scalars()
        return {document.id: document for document in rows}



RepositoryScope = Callable[[], AbstractAsyncContextManager[KnowledgeDocumentRepository]]


def repository_scope(sessionmaker: async_sessionmaker[AsyncSession]) -> RepositoryScope:
    """One short transaction per `async with` block: commit on success, rollback on error."""

    @asynccontextmanager
    async def scope() -> AsyncIterator[KnowledgeDocumentRepository]:
        async with sessionmaker() as session, session.begin():
            yield KnowledgeDocumentRepository(session)


    return scope
