from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.leads.enums import LeadIntent, LeadScoreCategory, LeadStatus
from app.modules.leads.models import Lead


class LeadRepository:
    """Async database operations for leads with strict tenant-isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        tenant_id: uuid.UUID,
        lead_data: dict[str, Any],
    ) -> Lead:
        lead = Lead(tenant_id=tenant_id, **lead_data)
        self._session.add(lead)
        await self._session.flush()
        await self._session.refresh(lead)
        return lead

    async def get_by_id(
        self,
        *,
        tenant_id: uuid.UUID,
        lead_id: uuid.UUID,
    ) -> Lead | None:
        stmt = select(Lead).where(
            Lead.id == lead_id,
            Lead.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_conversation_id(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> Lead | None:
        stmt = select(Lead).where(
            Lead.conversation_id == conversation_id,
            Lead.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_duplicate(
        self,
        *,
        tenant_id: uuid.UUID,
        phone: str | None = None,
        email: str | None = None,
    ) -> Lead | None:
        """Find an existing lead in the tenant by phone or email."""
        conditions = []
        if phone:
            conditions.append(Lead.phone == phone)
        if email:
            conditions.append(Lead.email == email)

        if not conditions:
            return None

        stmt = (
            select(Lead)
            .where(Lead.tenant_id == tenant_id, or_(*conditions))
            .order_by(desc(Lead.created_at))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_leads(
        self,
        *,
        tenant_id: uuid.UUID,
        status: LeadStatus | None = None,
        intent: LeadIntent | None = None,
        score_category: LeadScoreCategory | None = None,
        min_score: int | None = None,
        max_score: int | None = None,
        assigned_agent_id: uuid.UUID | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> tuple[Sequence[Lead], int]:
        """Query leads with filtering, search, and pagination."""
        stmt = select(Lead).where(Lead.tenant_id == tenant_id)
        count_stmt = select(func.count(Lead.id)).where(Lead.tenant_id == tenant_id)

        # Filters
        if status is not None:
            stmt = stmt.where(Lead.status == status)
            count_stmt = count_stmt.where(Lead.status == status)

        if intent is not None:
            stmt = stmt.where(Lead.intent == intent)
            count_stmt = count_stmt.where(Lead.intent == intent)

        if assigned_agent_id is not None:
            stmt = stmt.where(Lead.assigned_agent_id == assigned_agent_id)
            count_stmt = count_stmt.where(Lead.assigned_agent_id == assigned_agent_id)

        # Score category filter
        if score_category is not None:
            if score_category == LeadScoreCategory.HOT:
                stmt = stmt.where(Lead.ai_score >= 85)
                count_stmt = count_stmt.where(Lead.ai_score >= 85)
            elif score_category == LeadScoreCategory.WARM:
                stmt = stmt.where(Lead.ai_score >= 70, Lead.ai_score < 85)
                count_stmt = count_stmt.where(Lead.ai_score >= 70, Lead.ai_score < 85)
            elif score_category == LeadScoreCategory.COLD:
                stmt = stmt.where(Lead.ai_score < 70)
                count_stmt = count_stmt.where(Lead.ai_score < 70)

        if min_score is not None:
            stmt = stmt.where(Lead.ai_score >= min_score)
            count_stmt = count_stmt.where(Lead.ai_score >= min_score)

        if max_score is not None:
            stmt = stmt.where(Lead.ai_score <= max_score)
            count_stmt = count_stmt.where(Lead.ai_score <= max_score)

        if search and search.strip():
            term = f"%{search.strip()}%"
            search_clause = or_(
                Lead.contact_name.ilike(term),
                Lead.email.ilike(term),
                Lead.phone.ilike(term),
                Lead.preferred_location.ilike(term),
            )
            stmt = stmt.where(search_clause)
            count_stmt = count_stmt.where(search_clause)

        # Sorting
        sort_col = getattr(Lead, sort_by, Lead.created_at)
        stmt = stmt.order_by(desc(sort_col) if sort_desc else sort_col)
        stmt = stmt.offset(offset).limit(limit)

        total_res = await self._session.execute(count_stmt)
        total = total_res.scalar() or 0

        items_res = await self._session.execute(stmt)
        items = items_res.scalars().all()

        return items, total

    async def update(
        self,
        *,
        lead: Lead,
        update_data: dict[str, Any],
    ) -> Lead:
        for key, value in update_data.items():
            setattr(lead, key, value)
        await self._session.flush()
        await self._session.refresh(lead)
        return lead

    async def delete(
        self,
        *,
        tenant_id: uuid.UUID,
        lead_id: uuid.UUID,
    ) -> bool:
        stmt = delete(Lead).where(
            Lead.id == lead_id,
            Lead.tenant_id == tenant_id,
        )
        res = await self._session.execute(stmt)
        await self._session.flush()
        return res.rowcount > 0  # type: ignore[no-any-return]
