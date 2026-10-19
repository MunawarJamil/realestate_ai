from collections.abc import AsyncIterator
import json
import logging
from typing import Final, NoReturn
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.modules.auth.dependencies import AgencyUserContext, require_agency_user  # 12b HITL
from app.modules.chat.dependencies import get_chat_service
from app.modules.chat.exceptions import (
    ChatError,
    ChatServiceUnavailableError,
    ConversationNotFoundError,
    InvalidMessageError,
)
from app.modules.chat.enums import ConversationStatus
from app.modules.chat.schemas import (
    ConversationCreateRequest,
    ConversationList,
    ConversationRead,
    ConversationSummaryResponse,  # 12b HITL
    MessageRead,
    SendMessageRequest,
)
from app.modules.chat.service import ChatService
from app.modules.tenants.dependencies import get_current_tenant
from app.modules.tenants.models import Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_STATUS_BY_ERROR: Final[tuple[tuple[type[ChatError], int], ...]] = (
    (ConversationNotFoundError, status.HTTP_404_NOT_FOUND),
    (InvalidMessageError, status.HTTP_422_UNPROCESSABLE_ENTITY),
    (ChatServiceUnavailableError, status.HTTP_503_SERVICE_UNAVAILABLE),
)


def _raise_http(exc: ChatError) -> NoReturn:
    for error_cls, status_code in _STATUS_BY_ERROR:
        if isinstance(exc, error_cls):
            raise HTTPException(status_code=status_code, detail=str(exc))
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/conversations",
    response_model=ConversationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    body: ConversationCreateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    service: ChatService = Depends(get_chat_service),
) -> ConversationRead:
    try:
        conv = await service.create_conversation(
            tenant_id=tenant.id,
            title=body.title,
            metadata=body.metadata,
        )
        return ConversationRead.model_validate(conv)
    except ChatError as exc:
        _raise_http(exc)


@router.get(
    "/conversations",
    response_model=ConversationList,
)
async def list_conversations(
    status: ConversationStatus | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant: Tenant = Depends(get_current_tenant),
    service: ChatService = Depends(get_chat_service),
) -> ConversationList:
    items = await service.list_conversations(
        tenant_id=tenant.id, status=status, limit=limit, offset=offset
    )
    return ConversationList(
        items=[ConversationRead.model_validate(c) for c in items],
        total=len(items),
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationRead,
)
async def get_conversation(
    conversation_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    service: ChatService = Depends(get_chat_service),
) -> ConversationRead:
    try:
        conv = await service.get_conversation(
            tenant_id=tenant.id,
            conversation_id=conversation_id,
        )
        return ConversationRead.model_validate(conv)
    except ChatError as exc:
        _raise_http(exc)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageRead],
)
async def list_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tenant: Tenant = Depends(get_current_tenant),
    service: ChatService = Depends(get_chat_service),
) -> list[MessageRead]:
    try:
        messages = await service.list_messages(
            tenant_id=tenant.id,
            conversation_id=conversation_id,
            limit=limit,
            offset=offset,
        )
        return [MessageRead.model_validate(m) for m in messages]
    except ChatError as exc:
        _raise_http(exc)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageRead,
)
async def send_message(
    conversation_id: uuid.UUID,
    body: SendMessageRequest,
    tenant: Tenant = Depends(get_current_tenant),
    service: ChatService = Depends(get_chat_service),
) -> MessageRead:
    try:
        message = await service.send_message(
            tenant_id=tenant.id,
            conversation_id=conversation_id,
            user_message=body.content,
        )
        return MessageRead.model_validate(message)
    except ChatError as exc:
        _raise_http(exc)


async def _sse_streamer(tokens: AsyncIterator[str]) -> AsyncIterator[str]:
    try:
        async for token in tokens:
            payload = json.dumps({"token": token})
            yield f"data: {payload}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as exc:
        logger.error("SSE streaming error encountered: %r", exc)
        err_payload = json.dumps({"error": "Response stream interrupted"})
        yield f"event: error\ndata: {err_payload}\n\n"


@router.post(
    "/conversations/{conversation_id}/stream",
)
async def stream_chat(
    conversation_id: uuid.UUID,
    body: SendMessageRequest,
    tenant: Tenant = Depends(get_current_tenant),
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    # First verify conversation exists and message is valid before starting HTTP stream
    try:
        await service.get_conversation(tenant_id=tenant.id, conversation_id=conversation_id)
        if not body.content.strip():
            raise InvalidMessageError("Message content cannot be empty.")
    except ChatError as exc:
        _raise_http(exc)

    stream_generator = service.stream_chat(
        tenant_id=tenant.id,
        conversation_id=conversation_id,
        user_message=body.content,
    )

    return StreamingResponse(
        _sse_streamer(stream_generator),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# 12b HITL - Agent Claim Conversation Endpoint
@router.post(
    "/conversations/{conversation_id}/claim",
    response_model=ConversationRead,
)
async def claim_conversation(
    conversation_id: uuid.UUID,
    ctx: AgencyUserContext = Depends(require_agency_user),
    service: ChatService = Depends(get_chat_service),
) -> ConversationRead:
    try:
        conv = await service.claim_conversation(
            tenant_id=ctx.tenant.id,
            conversation_id=conversation_id,
            agent_id=ctx.user.id,
            agent_name=ctx.user.full_name,
        )
        return ConversationRead.model_validate(conv)
    except ChatError as exc:
        _raise_http(exc)


# 12b HITL - Agent Release Conversation back to AI Endpoint
@router.post(
    "/conversations/{conversation_id}/release",
    response_model=ConversationRead,
)
async def release_conversation(
    conversation_id: uuid.UUID,
    ctx: AgencyUserContext = Depends(require_agency_user),
    service: ChatService = Depends(get_chat_service),
) -> ConversationRead:
    try:
        conv = await service.release_conversation(
            tenant_id=ctx.tenant.id,
            conversation_id=conversation_id,
        )
        return ConversationRead.model_validate(conv)
    except ChatError as exc:
        _raise_http(exc)


# 12b HITL - Agent Resolve Conversation Endpoint
@router.post(
    "/conversations/{conversation_id}/resolve",
    response_model=ConversationRead,
)
async def resolve_conversation(
    conversation_id: uuid.UUID,
    ctx: AgencyUserContext = Depends(require_agency_user),
    service: ChatService = Depends(get_chat_service),
) -> ConversationRead:
    try:
        conv = await service.resolve_conversation(
            tenant_id=ctx.tenant.id,
            conversation_id=conversation_id,
        )
        return ConversationRead.model_validate(conv)
    except ChatError as exc:
        _raise_http(exc)


# 12b HITL - AI Handover Summary Endpoint
@router.get(
    "/conversations/{conversation_id}/summary",
    response_model=ConversationSummaryResponse,
)
async def get_conversation_summary(
    conversation_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    service: ChatService = Depends(get_chat_service),
) -> ConversationSummaryResponse:
    try:
        return await service.summarize_conversation(
            tenant_id=tenant.id,
            conversation_id=conversation_id,
        )
    except ChatError as exc:
        _raise_http(exc)

