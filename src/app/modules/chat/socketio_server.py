# 12c & 12d HITL - Socket.IO Real-Time Gateway (transport only, LangGraph lives in graph_runtime)
from __future__ import annotations
from app.core.config import Settings
import inspect
import logging
from typing import Any
from urllib.parse import parse_qs
import uuid
from datetime import UTC, datetime
import asyncio
import socketio
from socketio.exceptions import ConnectionRefusedError

from app.core.config import get_settings
from app.core.security import decode_user_token, decode_visitor_token
from app.db.session import get_sessionmaker
from app.modules.chat.enums import ConversationStatus, MessageRole, SenderType
from app.modules.chat.graph_runtime import run_visitor_turn, sync_agent_message
from app.modules.chat.repository import ChatRepository

logger = logging.getLogger(__name__)

MAX_MESSAGE_LEN = 4000

# ==============================================================================
# Socket.IO ASGI Server
# ==============================================================================


def _build_server() -> socketio.AsyncServer:
    settings = get_settings()

    # Restrict to real widget/dashboard domains in production.
    origins = getattr(settings, "socketio_cors_origins", None) or "*"
    if origins == "*":
        logger.warning("[Socket.IO] CORS is open to all origins, restrict in production")

    # Redis manager: rooms/emits are shared across multiple workers/instances.
    redis_url = getattr(settings, "redis_url", None)
    manager = socketio.AsyncRedisManager(str(redis_url)) if redis_url else None

    return socketio.AsyncServer(
        async_mode="asgi",
        cors_allowed_origins=origins,
        client_manager=manager,
        logger=False,
        engineio_logger=False,
    )


sio = _build_server()


# ==============================================================================
# Helpers
# ==============================================================================


def _payload(
    msg_id: uuid.UUID, conv_id: str, *, role: str, sender: str, content: str, **extra: Any
) -> dict[str, Any]:
    return {
        "id": str(msg_id),
        "conversation_id": conv_id,
        "role": role,
        "sender_type": sender,
        "content": content,
        "created_at": datetime.now(UTC).isoformat(),
        **extra,
    }


def _visitor_owns(conv: Any, session: dict[str, Any]) -> bool:
    """Visitors may only touch their own conversation (checked via metadata JSONB)."""
    if session["role"] != "visitor":
        return True
    meta = getattr(conv, "metadata_", {}) or {}
    visitor_id = meta.get("visitor_id") or getattr(conv, "visitor_id", None)
    return str(visitor_id) == str(session["user_id"])


def _parse_uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError):
        return None


def _decode_token(token: str) -> dict[str, Any] | None:
    """Returns a session dict for a valid visitor/agent token, else None."""
    secret = get_settings().secret_key.get_secret_value()

    try:
        payload = decode_visitor_token(token, secret)
        return {
            "tenant_id": uuid.UUID(payload["tenant_id"]),
            "user_id": str(payload["sub"]),
            "role": "visitor",
        }
    except Exception as exc:
        logger.debug("[Socket.IO] Not a visitor token: %r", exc)

    try:
        payload = decode_user_token(token, secret, expected_audience="agency")
        return {
            "tenant_id": uuid.UUID(payload["tenant_id"]),
            "user_id": uuid.UUID(payload["sub"]),
            "role": str(payload.get("role", "agent")),
        }
    except Exception as exc:
        logger.warning("[Socket.IO] Invalid token: %r", exc)
        return None


# ==============================================================================
# Connection lifecycle
# ==============================================================================


@sio.event
async def connect(sid: str, environ: dict[str, Any], auth: dict[str, Any] | None = None) -> None:
    token = (auth or {}).get("token")
    if not token:
        token_list = parse_qs(environ.get("QUERY_STRING", "")).get("token")
        token = token_list[0] if token_list else None
    if not token:
        logger.warning("[Socket.IO] Rejected: missing token sid=%s", sid)
        raise ConnectionRefusedError("Missing authentication token")

    session = _decode_token(token)
    if session is None:
        raise ConnectionRefusedError("Invalid authentication token")

    await sio.save_session(sid, session)
    if session["role"] != "visitor":
        await sio.enter_room(sid, f"tenant_{session['tenant_id']}_agents")
    logger.info(
        "[Socket.IO] Connected: sid=%s role=%s tenant=%s",
        sid,
        session["role"],
        session["tenant_id"],
    )


@sio.event
async def disconnect(sid: str) -> None:
    logger.info("[Socket.IO] Disconnected: sid=%s", sid)


@sio.event
async def join_conversation(sid: str, data: dict[str, Any]) -> dict[str, Any]:
    session = await sio.get_session(sid)
    if not session:
        return {"status": "error", "message": "Unauthenticated session"}

    conversation_id = _parse_uuid((data or {}).get("conversation_id"))
    if conversation_id is None:
        return {"status": "error", "message": "Invalid conversation_id"}

    async with get_sessionmaker()() as db:
        repo = ChatRepository(db)
        conv = await repo.get_conversation(
            tenant_id=session["tenant_id"], conversation_id=conversation_id
        )
        # Auto-heal: If visitor conversation was purged, provision a fresh one
        if (not conv or not _visitor_owns(conv, session)) and session["role"] == "visitor":
            conv = await repo.create_conversation(
                tenant_id=session["tenant_id"],
                title="Website Visitor Inquiry",
                metadata={"visitor_id": str(session["user_id"]), "source": "embed_widget"},
            )
            await db.commit()
            conversation_id = conv.id
            await sio.emit("conversation_recreated", {"conversation_id": str(conversation_id)}, room=sid)

    if not conv or not _visitor_owns(conv, session):
        return {"status": "error", "message": "Conversation not found"}

    conv_room = f"conv_{conversation_id}"
    await sio.enter_room(sid, conv_room)
    return {"status": "ok", "room": conv_room, "conversation_id": str(conversation_id)}


# ==============================================================================
# send_message (dispatch)
# ==============================================================================


@sio.event
async def send_message(sid: str, data: dict[str, Any]) -> dict[str, Any]:
    session = await sio.get_session(sid)
    if not session:
        return {"status": "error", "message": "Unauthenticated"}

    data = data or {}
    content = str(data.get("content", "")).strip()
    if not content or len(content) > MAX_MESSAGE_LEN:
        return {"status": "error", "message": "Invalid message"}
    conversation_id = _parse_uuid(data.get("conversation_id"))
    if conversation_id is None:
        return {"status": "error", "message": "Invalid conversation_id"}

    if session["role"] == "visitor":
        return await _handle_visitor_message(
            sid=sid, session=session, conversation_id=conversation_id, content=content
        )
    return await _handle_agent_message(
        tenant_id=session["tenant_id"],
        conversation_id=conversation_id,
        agent_id=session["user_id"],
        content=content,
    )


async def _handle_visitor_message(
    *, sid: str, session: dict[str, Any], conversation_id: uuid.UUID, content: str
) -> dict[str, Any]:
    tenant_id: uuid.UUID = session["tenant_id"]
    conv_id = str(conversation_id)
    conv_room = f"conv_{conv_id}"
    agents_room = f"tenant_{tenant_id}_agents"

    # Phase 1: short DB session, only to save the visitor message
    async with get_sessionmaker()() as db:
        repo = ChatRepository(db)
        conv = await repo.get_conversation(tenant_id=tenant_id, conversation_id=conversation_id)
        # Auto-heal: If deleted while visitor was active, recreate on the fly
        if not conv or not _visitor_owns(conv, session):
            conv = await repo.create_conversation(
                tenant_id=tenant_id,
                title="Website Visitor Inquiry",
                metadata={"visitor_id": str(session["user_id"]), "source": "embed_widget"},
            )
            conversation_id = conv.id
            conv_id = str(conversation_id)
            conv_room = f"conv_{conv_id}"
            await sio.enter_room(sid, conv_room)
            await sio.emit("conversation_recreated", {"conversation_id": conv_id}, room=sid)

        msg = await repo.create_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=MessageRole.USER,
            sender_type=SenderType.VISITOR,
            content=content,
        )
        await db.commit()
        msg_id = msg.id
        conv_status = conv.status
        assigned_agent_id = conv.assigned_agent_id

    visitor_payload = _payload(msg_id, conv_id, role="user", sender="visitor", content=content)
    await sio.emit("new_message", visitor_payload, room=conv_room)
    await sio.emit("visitor_activity", visitor_payload, room=agents_room)

    # Phase 2: graph run (no DB session held)
    ai_turn = conv_status == ConversationStatus.AI
    if ai_turn:
        await sio.emit(
            "user_typing",
            {"conversation_id": conv_id, "is_typing": True, "sender": "ai"},
            room=conv_room,
        )
    try:
        result = await run_visitor_turn(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            content=content,
            status=conv_status.value,
            assigned_agent_id=assigned_agent_id,
        )
    finally:
        if ai_turn:
            await sio.emit(
                "user_typing",
                {"conversation_id": conv_id, "is_typing": False, "sender": "ai"},
                room=conv_room,
            )

    if result is None:
        await sio.emit(
            "ai_error", {"conversation_id": conv_id, "message": "Please try again."}, room=sid
        )
        return {"status": "ok", "message_id": str(msg_id)}

    # Phase 3: sync DB with graph decision, save AI reply (short session)
    graph_status = result.get("status")
    reply = result.get("reply_content")
    handoff_event: dict[str, Any] | None = None
    ai_resumed = False
    ai_payload: dict[str, Any] | None = None

    async with get_sessionmaker()() as db:
        repo = ChatRepository(db)

        if graph_status == "handoff_requested" and conv_status not in (
            ConversationStatus.HANDOFF_REQUESTED,
            ConversationStatus.HUMAN_ACTIVE,
        ):
            await repo.update_conversation_status(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                status=ConversationStatus.HANDOFF_REQUESTED,
            )
            handoff_event = {
                "conversation_id": conv_id,
                "reason": result.get("handoff_reason") or "user_request",
                "visitor_message": content,
                "created_at": datetime.now(UTC).isoformat(),
            }
        elif graph_status == "ai" and conv_status != ConversationStatus.AI:
            # 5-min inactivity / unclaimed handoff / reopened resolved conversation
            await repo.update_conversation_status(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                status=ConversationStatus.AI,
                assigned_agent_id=None,
            )
            ai_resumed = True

        if reply:
            ai_msg = await repo.create_message(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                sender_type=SenderType.AI,
                content=reply,
            )
            ai_payload = _payload(ai_msg.id, conv_id, role="assistant", sender="ai", content=reply)

        await db.commit()

    # Emit only after commit
    if handoff_event:
        await sio.emit("handoff_requested", handoff_event, room=agents_room)
    if ai_resumed:
        await sio.emit("ai_resumed", {"conversation_id": conv_id}, room=agents_room)
    if ai_payload:
        await sio.emit("new_message", ai_payload, room=conv_room)

    # Spawn non-blocking lead qualification analysis
    asyncio.create_task(
        _async_extract_lead(tenant_id=tenant_id, conversation_id=conversation_id)
    )

    return {"status": "ok", "message_id": str(msg_id)}


async def _handle_agent_message(
    *, tenant_id: uuid.UUID, conversation_id: uuid.UUID, agent_id: uuid.UUID, content: str
) -> dict[str, Any]:
    conv_id = str(conversation_id)

    async with get_sessionmaker()() as db:
        repo = ChatRepository(db)
        conv = await repo.get_conversation(tenant_id=tenant_id, conversation_id=conversation_id)
        if not conv:
            return {"status": "error", "message": "Conversation not found"}

        msg = await repo.create_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            sender_type=SenderType.AGENT,
            agent_id=agent_id,
            content=content,
        )
        if conv.status != ConversationStatus.HUMAN_ACTIVE or conv.assigned_agent_id != agent_id:
            await repo.update_conversation_status(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                status=ConversationStatus.HUMAN_ACTIVE,
                assigned_agent_id=agent_id,
            )
        await db.commit()
        msg_id = msg.id

    await sync_agent_message(
        tenant_id=tenant_id, conversation_id=conversation_id, agent_id=agent_id, content=content
    )

    await sio.emit(
        "new_message",
        _payload(
            msg_id,
            conv_id,
            role="assistant",
            sender="agent",
            content=content,
            agent_id=str(agent_id),
        ),
        room=f"conv_{conv_id}",
    )
    return {"status": "ok", "message_id": str(msg_id)}


# ==============================================================================
# Typing indicator
# ==============================================================================


@sio.event
async def typing(sid: str, data: dict[str, Any]) -> None:
    session = await sio.get_session(sid)
    data = data or {}
    conversation_id = _parse_uuid(data.get("conversation_id"))
    if not session or conversation_id is None:
        return

    conv_room = f"conv_{conversation_id}"
    # Only sockets that already joined (and were authorized for) this room may type in it.
    joined = sio.rooms(sid)
    if inspect.isawaitable(joined):
        joined = await joined
    if conv_room not in joined:
        return

    await sio.emit(
        "user_typing",
        {
            "conversation_id": str(conversation_id),
            "is_typing": bool(data.get("is_typing", True)),
            "sender": "visitor" if session["role"] == "visitor" else "agent",
        },
        room=conv_room,
        skip_sid=sid,
    )




async def _async_extract_lead(*, tenant_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
    """Non-blocking background extraction worker running after conversation turn."""
    try:
        from app.core.config import get_settings
        from app.db.session import get_sessionmaker
        from app.integrations.llm.client import build_llm_client
        from app.modules.leads.extractor import LeadExtractionEngine
        from app.modules.leads.repository import LeadRepository
        from app.modules.leads.service import LeadService

        async with get_sessionmaker()() as db:
            repo = ChatRepository(db)
            messages = await repo.list_messages(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                limit=50,
                offset=0,
            )
            if not messages:
                return

            lead_service = LeadService(LeadRepository(db))
            engine = LeadExtractionEngine(
                llm=build_llm_client(get_settings()),
                lead_service=lead_service,
            )
            await engine.extract_and_qualify(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                messages=list(messages),
            )
            await db.commit()
    except Exception as exc:
        logger.warning(
            "Background lead extraction error for conversation_id=%s: %r",
            conversation_id,
            exc,
        )
