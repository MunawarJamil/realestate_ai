from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bookings.enums import BookingStatus
from app.modules.bookings.models import ViewingBooking


class BookingRepository:
    """Pure async DB operations for viewing bookings with strict tenant-isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Create 

    async def create(
        self,
        *,
        tenant_id: uuid.UUID,
        booking_data: dict[str, Any],
    ) -> ViewingBooking:
        booking = ViewingBooking(tenant_id=tenant_id, **booking_data)
        self._session.add(booking)
        await self._session.flush()
        await self._session.refresh(booking)
        return booking

    # ── Reads ────────────────────────────────────────────────────────────────

    async def get_by_id(
        self,
        *,
        tenant_id: uuid.UUID,
        booking_id: uuid.UUID,
    ) -> ViewingBooking | None:
        stmt = select(ViewingBooking).where(
            ViewingBooking.id == booking_id,
            ViewingBooking.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_conversation_id(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> Sequence[ViewingBooking]:
        """Return all bookings linked to a conversation (a visitor may book multiple slots)."""
        stmt = (
            select(ViewingBooking)
            .where(
                ViewingBooking.conversation_id == conversation_id,
                ViewingBooking.tenant_id == tenant_id,
            )
            .order_by(desc(ViewingBooking.preferred_time))
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    # ── Rate-limit check ─────────────────────────────────────────────────────

    async def count_bookings_today(
        self,
        *,
        tenant_id: uuid.UUID,
        phone: str,
    ) -> int:
        """Count bookings for a visitor phone number created today (UTC calendar day).

        Used to enforce the max 3 bookings/day rate limit per visitor.
        """
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        stmt = select(func.count(ViewingBooking.id)).where(
            ViewingBooking.tenant_id == tenant_id,
            ViewingBooking.phone == phone,
            ViewingBooking.created_at >= today_start,
            # Only count active bookings — cancellations don't consume quota
            ViewingBooking.status != BookingStatus.CANCELED,
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    # ── List with filters & pagination ───────────────────────────────────────

    async def list_bookings(
        self,
        *,
        tenant_id: uuid.UUID,
        status: BookingStatus | None = None,
        assigned_agent_id: uuid.UUID | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
        sort_by: str = "preferred_time",
        sort_desc: bool = False,
    ) -> tuple[Sequence[ViewingBooking], int]:
        base_filter = [ViewingBooking.tenant_id == tenant_id]

        if status is not None:
            base_filter.append(ViewingBooking.status == status)
        if assigned_agent_id is not None:
            base_filter.append(ViewingBooking.assigned_agent_id == assigned_agent_id)
        if from_time is not None:
            base_filter.append(ViewingBooking.preferred_time >= from_time)
        if to_time is not None:
            base_filter.append(ViewingBooking.preferred_time <= to_time)
        if search and search.strip():
            term = f"%{search.strip()}%"
            base_filter.append(
                or_(
                    ViewingBooking.visitor_name.ilike(term),
                    ViewingBooking.phone.ilike(term),
                    ViewingBooking.property_ref.ilike(term),
                )
            )

        where_clause = and_(*base_filter)
        count_stmt = select(func.count(ViewingBooking.id)).where(where_clause)
        sort_col = getattr(ViewingBooking, sort_by, ViewingBooking.preferred_time)
        items_stmt = (
            select(ViewingBooking)
            .where(where_clause)
            .order_by(desc(sort_col) if sort_desc else sort_col)
            .offset(offset)
            .limit(limit)
        )

        total = (await self._session.execute(count_stmt)).scalar() or 0
        items = (await self._session.execute(items_stmt)).scalars().all()
        return items, total

    # ── Upd────

    async def update(
        self,
        *,
        booking: ViewingBooking,
        update_data: dict[str, Any],
    ) -> ViewingBooking:
        for key, value in update_data.items():
            setattr(booking, key, value)
        await self._session.flush()
        await self._session.refresh(booking)
        return booking

    # ── Delete 

    async def delete(
        self,
        *,
        tenant_id: uuid.UUID,
        booking_id: uuid.UUID,
    ) -> bool:
        stmt = delete(ViewingBooking).where(
            ViewingBooking.id == booking_id,
            ViewingBooking.tenant_id == tenant_id,
        )
        res = await self._session.execute(stmt)
        await self._session.flush()
        return res.rowcount > 0  # type: ignore[no-any-return]