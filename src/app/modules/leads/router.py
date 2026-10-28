from __future__ import annotations

import logging
import uuid
from typing import Final, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from app.modules.chat.dependencies import get_llm_client
from app.modules.chat.repository import ChatRepository
from app.modules.leads.extractor import LeadExtractionEngine
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from app.integrations.llm.base import LLMProvider
from app.modules.leads.dependencies import get_lead_service
from app.modules.leads.enums import LeadIntent, LeadScoreCategory, LeadStatus
from app.modules.leads.exceptions import (
    InvalidLeadStatusTransitionError,
    LeadError,
    LeadNotFoundError,
    LeadValidationError,
)
from app.modules.leads.schemas import (
    LeadCreate,
    LeadListResponse,
    LeadRead,
    LeadUpdate,
)
from app.modules.leads.service import LeadService
from app.modules.tenants.dependencies import get_current_tenant
from app.modules.tenants.models import Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["leads"])

_STATUS_BY_ERROR: Final[tuple[tuple[type[LeadError], int], ...]] = (
    (LeadNotFoundError, status.HTTP_404_NOT_FOUND),
    (InvalidLeadStatusTransitionError, status.HTTP_422_UNPROCESSABLE_ENTITY),
    (LeadValidationError, status.HTTP_422_UNPROCESSABLE_ENTITY),
)


def _raise_http(exc: LeadError) -> NoReturn:
    for error_cls, status_code in _STATUS_BY_ERROR:
        if isinstance(exc, error_cls):
            raise HTTPException(status_code=status_code, detail=str(exc))
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


class AssignLeadRequest(BaseModel):
    assigned_agent_id: uuid.UUID | None = None


@router.post(
    "",
    response_model=LeadRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new lead manually",
)
async def create_lead(
    body: LeadCreate,
    tenant: Tenant = Depends(get_current_tenant),
    service: LeadService = Depends(get_lead_service),
) -> LeadRead:
    try:
        return await service.create_lead(tenant_id=tenant.id, data=body)
    except LeadError as exc:
        _raise_http(exc)


@router.get(
    "",
    response_model=LeadListResponse,
    summary="List leads with search, filtering, and pagination",
)
async def list_leads(
    status: LeadStatus | None = Query(None, description="Filter by lead status"),
    intent: LeadIntent | None = Query(None, description="Filter by intent (buy/rent/invest/sell)"),
    score_category: LeadScoreCategory | None = Query(None, description="Filter by hot, warm, or cold"),
    min_score: int | None = Query(None, ge=0, le=100, description="Minimum AI score"),
    max_score: int | None = Query(None, ge=0, le=100, description="Maximum AI score"),
    assigned_agent_id: uuid.UUID | None = Query(None, description="Filter by assigned broker"),
    search: str | None = Query(None, description="Search across name, email, phone, location"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: str = Query("created_at", description="Sort field: created_at, ai_score, etc."),
    sort_desc: bool = Query(True, description="Sort descending"),
    tenant: Tenant = Depends(get_current_tenant),
    service: LeadService = Depends(get_lead_service),
) -> LeadListResponse:
    try:
        return await service.list_leads(
            tenant_id=tenant.id,
            status=status,
            intent=intent,
            score_category=score_category,
            min_score=min_score,
            max_score=max_score,
            assigned_agent_id=assigned_agent_id,
            search=search,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )
    except LeadError as exc:
        _raise_http(exc)





@router.get(
    "/{lead_id}",
    response_model=LeadRead,
    summary="Get single lead details",
)
async def get_lead(
    lead_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    service: LeadService = Depends(get_lead_service),
) -> LeadRead:
    try:
        return await service.get_lead(tenant_id=tenant.id, lead_id=lead_id)
    except LeadError as exc:
        _raise_http(exc)


@router.patch(
    "/{lead_id}",
    response_model=LeadRead,
    summary="Update lead fields or lifecycle status",
)
async def update_lead(
    lead_id: uuid.UUID,
    body: LeadUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    service: LeadService = Depends(get_lead_service),
) -> LeadRead:
    try:
        return await service.update_lead(
            tenant_id=tenant.id,
            lead_id=lead_id,
            data=body,
        )
    except LeadError as exc:
        _raise_http(exc)


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a lead",
)
async def delete_lead(
    lead_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    service: LeadService = Depends(get_lead_service),
) -> None:
    try:
        await service.delete_lead(tenant_id=tenant.id, lead_id=lead_id)
    except LeadError as exc:
        _raise_http(exc)


@router.post(
    "/{lead_id}/assign",
    response_model=LeadRead,
    summary="Assign or reassign a lead to a broker agent",
)
async def assign_lead(
    lead_id: uuid.UUID,
    body: AssignLeadRequest,
    tenant: Tenant = Depends(get_current_tenant),
    service: LeadService = Depends(get_lead_service),
) -> LeadRead:
    try:
        return await service.update_lead(
            tenant_id=tenant.id,
            lead_id=lead_id,
            data=LeadUpdate(assigned_agent_id=body.assigned_agent_id),
        )
    except LeadError as exc:
        _raise_http(exc)




@router.post(
    "/extract/{conversation_id}",
    response_model=LeadRead | None,
    summary="Trigger on-demand AI lead extraction for a conversation",
)
async def extract_lead_from_conversation(
    conversation_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    service: LeadService = Depends(get_lead_service),
    llm: LLMProvider = Depends(get_llm_client),
    session: AsyncSession = Depends(get_session),
) -> LeadRead | None:
    chat_repo = ChatRepository(session)
    messages = await chat_repo.list_messages(
        tenant_id=tenant.id,
        conversation_id=conversation_id,
        limit=50,
        offset=0,
    )
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation has no messages to extract from.",
        )
    engine = LeadExtractionEngine(llm=llm, lead_service=service)
    lead = await engine.extract_and_qualify(
        tenant_id=tenant.id,
        conversation_id=conversation_id,
        messages=list(messages),
    )
    return lead


