"""FastAPI router for public embeddable widget session and chat operations."""

from collections.abc import AsyncIterator
import json
import logging
from typing import Final, NoReturn
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.modules.chat.dependencies import get_chat_service
from app.modules.chat.exceptions import (
    ChatError,
    ChatServiceUnavailableError,
    ConversationNotFoundError,
    InvalidMessageError,
)
from app.modules.chat.schemas import (
    ConversationCreateRequest,
    ConversationList,
    ConversationRead,
    MessageRead,
    SendMessageRequest,
)
from app.modules.chat.service import ChatService
from app.modules.tenants.models import Tenant
from app.modules.widget.dependencies import (
    VisitorContext,
    get_current_visitor,
    get_widget_tenant,
)
from app.modules.widget.rate_limiter import rate_limit_chat_stream, rate_limit_visitor
from app.modules.widget.schemas import (
    VisitorContextRead,
    WidgetSessionInitRequest,
    WidgetSessionResponse,
)
from app.modules.widget.service import WidgetService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/widget", tags=["widget"])

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


# ==============================================================================
# Widget Session & Identity Endpoints
# ==============================================================================


@router.post(
    "/session",
    response_model=WidgetSessionResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit_visitor)],
    summary="Initialize or resume a visitor session",
)
async def init_widget_session(
    body: WidgetSessionInitRequest | None = None,
    tenant: Tenant = Depends(get_widget_tenant),
    settings: Settings = Depends(get_settings),
) -> WidgetSessionResponse:
    """Authenticates the public widget key and caller Origin, issuing an isolated visitor JWT."""
    service = WidgetService(secret_key=settings.secret_key.get_secret_value())
    requested_id = body.visitor_id if body is not None else None
    return service.create_or_resume_session(
        tenant=tenant,
        requested_visitor_id=requested_id,
    )


@router.get(
    "/session/verify",
    response_model=VisitorContextRead,
    summary="Verify current visitor session token",
)
async def verify_widget_session(
    visitor: VisitorContext = Depends(get_current_visitor),
) -> VisitorContextRead:
    """Verifies that the visitor's JWT Bearer token is valid and active."""
    return VisitorContextRead(
        visitor_id=visitor.visitor_id,
        tenant_id=visitor.tenant_id,
        tenant_name=visitor.tenant.name,
    )


# ==============================================================================
# Visitor-Isolated Conversation Endpoints
# ==============================================================================


@router.post(
    "/conversations",
    response_model=ConversationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_visitor)],
    summary="Create a new conversation for the authenticated visitor",
)
async def create_widget_conversation(
    body: ConversationCreateRequest | None = None,
    visitor: VisitorContext = Depends(get_current_visitor),
    service: ChatService = Depends(get_chat_service),
) -> ConversationRead:
    """Creates a conversation strictly attached to the visitor's UUID for isolation."""
    metadata = {
        "visitor_id": str(visitor.visitor_id),
        "source": "embed_widget",
    }
    if body and body.metadata:
        metadata.update(body.metadata)

    title = body.title if body else "New Conversation"

    try:
        conv = await service.create_conversation(
            tenant_id=visitor.tenant_id,
            title=title,
            metadata=metadata,
        )
        return ConversationRead.model_validate(conv)
    except ChatError as exc:
        _raise_http(exc)


@router.get(
    "/conversations",
    response_model=ConversationList,
    dependencies=[Depends(rate_limit_visitor)],
    summary="List conversations belonging strictly to this visitor",
)
async def list_widget_conversations(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    visitor: VisitorContext = Depends(get_current_visitor),
    service: ChatService = Depends(get_chat_service),
) -> ConversationList:
    items = await service.list_conversations_for_visitor(
        tenant_id=visitor.tenant_id,
        visitor_id=str(visitor.visitor_id),
        limit=limit,
        offset=offset,
    )
    return ConversationList(
        items=[ConversationRead.model_validate(c) for c in items],
        total=len(items),
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationRead,
    dependencies=[Depends(rate_limit_visitor)],
    summary="Get conversation details verifying visitor ownership",
)
async def get_widget_conversation(
    conversation_id: uuid.UUID,
    visitor: VisitorContext = Depends(get_current_visitor),
    service: ChatService = Depends(get_chat_service),
) -> ConversationRead:
    try:
        conv = await service.get_conversation_for_visitor(
            tenant_id=visitor.tenant_id,
            conversation_id=conversation_id,
            visitor_id=str(visitor.visitor_id),
        )
        return ConversationRead.model_validate(conv)
    except ChatError as exc:
        _raise_http(exc)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageRead],
    dependencies=[Depends(rate_limit_visitor)],
    summary="List message history in visitor's conversation",
)
async def list_widget_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    visitor: VisitorContext = Depends(get_current_visitor),
    service: ChatService = Depends(get_chat_service),
) -> list[MessageRead]:
    try:
        # First assert ownership through service
        await service.get_conversation_for_visitor(
            tenant_id=visitor.tenant_id,
            conversation_id=conversation_id,
            visitor_id=str(visitor.visitor_id),
        )
        messages = await service.list_messages(
            tenant_id=visitor.tenant_id,
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
    dependencies=[Depends(rate_limit_chat_stream)],
    summary="Send message and receive complete assistant reply (REST mode)",
)
async def send_widget_message(
    conversation_id: uuid.UUID,
    body: SendMessageRequest,
    visitor: VisitorContext = Depends(get_current_visitor),
    service: ChatService = Depends(get_chat_service),
) -> MessageRead:
    try:
        await service.get_conversation_for_visitor(
            tenant_id=visitor.tenant_id,
            conversation_id=conversation_id,
            visitor_id=str(visitor.visitor_id),
        )
        reply = await service.send_message(
            tenant_id=visitor.tenant_id,
            conversation_id=conversation_id,
            user_message=body.content,
        )
        return MessageRead.model_validate(reply)
    except ChatError as exc:
        _raise_http(exc)


async def _widget_sse_streamer(tokens: AsyncIterator[str]) -> AsyncIterator[str]:
    try:
        async for token in tokens:
            payload = json.dumps({"token": token})
            yield f"data: {payload}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as exc:
        logger.error("Widget SSE stream interrupted: %r", exc)
        err_payload = json.dumps({"error": "Response stream interrupted"})
        yield f"event: error\ndata: {err_payload}\n\n"


@router.post(
    "/conversations/{conversation_id}/stream",
    dependencies=[Depends(rate_limit_chat_stream)],
    summary="Send message and stream assistant reply token-by-token (SSE mode)",
)
async def stream_widget_chat(
    conversation_id: uuid.UUID,
    body: SendMessageRequest,
    visitor: VisitorContext = Depends(get_current_visitor),
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    try:
        await service.get_conversation_for_visitor(
            tenant_id=visitor.tenant_id,
            conversation_id=conversation_id,
            visitor_id=str(visitor.visitor_id),
        )
    except ChatError as exc:
        _raise_http(exc)

    if not body.content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content cannot be empty",
        )

    stream_generator = service.stream_chat(
        tenant_id=visitor.tenant_id,
        conversation_id=conversation_id,
        user_message=body.content,
    )

    return StreamingResponse(
        _widget_sse_streamer(stream_generator),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
