from __future__ import annotations

import logging
import math
import uuid
from typing import Any

from app.modules.leads.enums import LeadIntent, LeadScoreCategory, LeadStatus
from app.modules.leads.exceptions import (
    InvalidLeadStatusTransitionError,
    LeadNotFoundError,
)
from app.modules.leads.models import Lead
from app.modules.leads.repository import LeadRepository
from app.modules.leads.schemas import (
    LeadCreate,
    LeadListResponse,
    LeadRead,
    LeadUpdate,
)

logger = logging.getLogger(__name__)

# Valid CRM status progression
VALID_STATUS_TRANSITIONS: dict[LeadStatus, set[LeadStatus]] = {
    LeadStatus.NEW: {LeadStatus.CONTACTED, LeadStatus.QUALIFIED, LeadStatus.LOST, LeadStatus.CLOSED},
    LeadStatus.CONTACTED: {LeadStatus.QUALIFIED, LeadStatus.LOST, LeadStatus.CLOSED, LeadStatus.NEW},
    LeadStatus.QUALIFIED: {LeadStatus.CLOSED, LeadStatus.LOST, LeadStatus.CONTACTED, LeadStatus.NEW},
    LeadStatus.LOST: {LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.QUALIFIED},
    LeadStatus.CLOSED: {LeadStatus.NEW, LeadStatus.QUALIFIED},
}



async def _broadcast_lead_event(event_name: str, lead: LeadRead) -> None:
    try:
        from app.modules.chat.socketio_server import sio
        payload = lead.model_dump(mode="json")
        await sio.emit(event_name, payload, room=f"tenant_{lead.tenant_id}_agents")
        if lead.ai_score >= 85:
            await sio.emit("hot_lead_alert", payload, room=f"tenant_{lead.tenant_id}_agents")
    except Exception as exc:
        logger.warning("Failed to broadcast lead event %s: %r", event_name, exc)


class LeadService:
    """Business operations and lifecycle management for leads."""

    def __init__(self, repository: LeadRepository) -> None:
        self._repository = repository

    async def create_lead(
        self,
        *,
        tenant_id: uuid.UUID,
        data: LeadCreate,
    ) -> LeadRead:
        lead_dict = data.model_dump(exclude_unset=True)
        lead = await self._repository.create(
            tenant_id=tenant_id,
            lead_data=lead_dict,
        )

        





        logger.info(
            "Lead created id=%s tenant_id=%s ai_score=%d",
            lead.id,
            tenant_id,
            lead.ai_score,
        )
        lead_read = LeadRead.model_validate(lead)
        await _broadcast_lead_event("lead_created", lead_read)
        return lead_read

    async def get_lead(
        self,
        *,
        tenant_id: uuid.UUID,
        lead_id: uuid.UUID,
    ) -> LeadRead:
        lead = await self._repository.get_by_id(tenant_id=tenant_id, lead_id=lead_id)
        if not lead:
            raise LeadNotFoundError(f"Lead {lead_id} not found.")
        return LeadRead.model_validate(lead)

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
        page: int = 1,
        size: int = 20,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> LeadListResponse:
        offset = (page - 1) * size
        leads, total = await self._repository.list_leads(
            tenant_id=tenant_id,
            status=status,
            intent=intent,
            score_category=score_category,
            min_score=min_score,
            max_score=max_score,
            assigned_agent_id=assigned_agent_id,
            search=search,
            offset=offset,
            limit=size,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )

        pages = math.ceil(total / size) if size > 0 else 0
        items = [LeadRead.model_validate(l) for l in leads]

        return LeadListResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    async def update_lead(
        self,
        *,
        tenant_id: uuid.UUID,
        lead_id: uuid.UUID,
        data: LeadUpdate,
    ) -> LeadRead:
        lead = await self._repository.get_by_id(tenant_id=tenant_id, lead_id=lead_id)
        if not lead:
            raise LeadNotFoundError(f"Lead {lead_id} not found.")

        update_dict = data.model_dump(exclude_unset=True)

        # Validate status transition if status is being updated
        if "status" in update_dict and update_dict["status"] is not None:
            new_status: LeadStatus = update_dict["status"]
            if new_status != lead.status:
                allowed = VALID_STATUS_TRANSITIONS.get(lead.status, set())
                if new_status not in allowed:
                    raise InvalidLeadStatusTransitionError(
                        f"Cannot transition lead from '{lead.status.value}' to '{new_status.value}'."
                    )

        updated_lead = await self._repository.update(
            lead=lead,
            update_data=update_dict,
        )
        logger.info("Lead updated id=%s tenant_id=%s", lead_id, tenant_id)

        lead_read = LeadRead.model_validate(updated_lead)
        await _broadcast_lead_event("lead_updated", lead_read)
        return lead_read

    async def delete_lead(
        self,
        *,
        tenant_id: uuid.UUID,
        lead_id: uuid.UUID,
    ) -> None:
        deleted = await self._repository.delete(tenant_id=tenant_id, lead_id=lead_id)
        if not deleted:
            raise LeadNotFoundError(f"Lead {lead_id} not found.")
        logger.info("Lead deleted id=%s tenant_id=%s", lead_id, tenant_id)

    async def upsert_from_conversation(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        lead_data: dict[str, Any],
    ) -> LeadRead:
        """Find existing lead by conversation or phone/email, and update or create."""
        lead = await self._repository.get_by_conversation_id(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
        )

        if not lead:
            # Check duplicate by contact details
            lead = await self._repository.find_duplicate(
                tenant_id=tenant_id,
                phone=lead_data.get("phone"),
                email=lead_data.get("email"),
            )

        if lead:
            # Retain non-null updates and highest score
            if "ai_score" in lead_data and lead_data["ai_score"] < lead.ai_score:
                lead_data.pop("ai_score", None)
                lead_data.pop("score_breakdown", None)

            # Do not overwrite conversation_id if already present
            if lead.conversation_id and "conversation_id" in lead_data:
                lead_data.pop("conversation_id", None)

            # Strip None values
            clean_updates = {k: v for k, v in lead_data.items() if v is not None}
            updated = await self._repository.update(lead=lead, update_data=clean_updates)
            return LeadRead.model_validate(updated)

        lead_data["conversation_id"] = conversation_id
        new_lead = await self._repository.create(
            tenant_id=tenant_id,
            lead_data=lead_data,
        )
        lead_read = LeadRead.model_validate(updated if lead else new_lead)
        await _broadcast_lead_event("lead_updated" if lead else "lead_created", lead_read)
        return lead_read

