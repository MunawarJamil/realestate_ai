# 12b HITL - Dual WebSocket Gateway (Visitor & Agent)
from datetime import UTC, datetime
import json
import logging
from typing import Any
import uuid

from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from app.core.config import get_settings
from app.core.security import decode_user_token, decode_visitor_token
from app.db.session import get_sessionmaker
from app.integrations.llm.client import build_llm_client
from app.modules.chat.connection_manager import (
    ConnectionManager,
    get_connection_manager,
)
from app.modules.chat.enums import ConversationStatus, MessageRole, SenderType
from app.modules.chat.events import (
    MessagePayload,
    StatusChangePayload,
    WSEvent,
    WSEventType,
)
from app.modules.chat.handoff import HANDOFF_GUARDRAIL_REPLY, detect_handoff_request
from app.modules.chat.repository import ChatRepository
from app.modules.chat.service import ChatService
from app.modules.knowledge.dependencies import get_retrieval_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat/ws", tags=["chat-realtime"])


# ==============================================================================
# 1. Agent WebSocket Gateway: /api/v1/chat/ws/agent
# (Defined FIRST so static '/agent' is matched before dynamic '/{conversation_id}')
# ==============================================================================


@router.websocket("/agent")
async def agent_websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None),
) -> None:
    """Real-time bi-directional WebSocket gateway for agency brokers and agents."""
    # 12b HITL
    settings = get_settings()

    token = token or websocket.query_params.get("token")
    if not token:
        await websocket.accept()
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing agent JWT token")
        return

    try:
        payload = decode_user_token(token, settings.secret_key.get_secret_value(), expected_audience="agency")
        tenant_id = uuid.UUID(payload["tenant_id"])
        user_id = uuid.UUID(payload["sub"])
        role = str(payload.get("role", ""))
        if role not in ("agency_admin", "agent"):
            await websocket.accept()
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized agent role")
            return
    except Exception as exc:
        logger.warning("Invalid agent WS auth token: %r", exc)
        await websocket.accept()
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid agent JWT")
        return

    conn_mgr = get_connection_manager()

    # Connect agent to receive tenant-wide alerts
    await conn_mgr.connect_agent(tenant_id, user_id, websocket)

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                frame: dict[str, Any] = json.loads(raw_text)
            except Exception:
                continue

            action = frame.get("action")

            if frame.get("type") == "ping":
                await websocket.send_json({"event": "pong", "timestamp": datetime.now(UTC).isoformat()})
                continue

            conv_id_str = frame.get("conversation_id")
            if not conv_id_str:
                continue
            conversation_id = uuid.UUID(conv_id_str)

            async with get_sessionmaker()() as session:
                repo = ChatRepository(session)
                conv = await repo.get_conversation(tenant_id=tenant_id, conversation_id=conversation_id)
                if not conv:
                    await websocket.send_json({"event": "error", "message": "Conversation not found"})
                    continue

                # 1. Action: Claim Conversation
                if action == "claim":
                    conv.status = ConversationStatus.HUMAN_ACTIVE
                    conv.assigned_agent_id = user_id

                    # Create system audit message
                    sys_msg = await repo.create_message(
                        tenant_id=tenant_id,
                        conversation_id=conversation_id,
                        role=MessageRole.SYSTEM,
                        sender_type=SenderType.SYSTEM,
                        agent_id=user_id,
                        content="A licensed property advisor has joined the live chat.",
                    )
                    await session.commit()

                    status_event = WSEvent(
                        event=WSEventType.STATUS_CHANGE,
                        conversation_id=conversation_id,
                        tenant_id=tenant_id,
                        payload=StatusChangePayload(
                            status=ConversationStatus.HUMAN_ACTIVE,
                            assigned_agent_id=user_id,
                        ).model_dump(mode="json"),
                    )
                    await conn_mgr.broadcast_conversation_event(tenant_id, conversation_id, status_event)
                    await conn_mgr.broadcast_agent_alert(tenant_id, status_event)

                # 2. Action: Release Conversation back to AI
                elif action == "release":
                    conv.status = ConversationStatus.AI
                    conv.assigned_agent_id = None

                    sys_msg = await repo.create_message(
                        tenant_id=tenant_id,
                        conversation_id=conversation_id,
                        role=MessageRole.SYSTEM,
                        sender_type=SenderType.SYSTEM,
                        content="Conversation transferred back to AI Concierge.",
                    )
                    await session.commit()

                    status_event = WSEvent(
                        event=WSEventType.STATUS_CHANGE,
                        conversation_id=conversation_id,
                        tenant_id=tenant_id,
                        payload=StatusChangePayload(
                            status=ConversationStatus.AI,
                            assigned_agent_id=None,
                        ).model_dump(mode="json"),
                    )
                    await conn_mgr.broadcast_conversation_event(tenant_id, conversation_id, status_event)
                    await conn_mgr.broadcast_agent_alert(tenant_id, status_event)

                # 3. Action: Send Human Agent Message
                elif action == "send_message":
                    content = str(frame.get("content", "")).strip()
                    if not content:
                        continue

                    agent_msg = await repo.create_message(
                        tenant_id=tenant_id,
                        conversation_id=conversation_id,
                        role=MessageRole.ASSISTANT,
                        sender_type=SenderType.AGENT,
                        agent_id=user_id,
                        content=content,
                    )
                    await session.commit()

                    msg_event = WSEvent(
                        event=WSEventType.MESSAGE,
                        conversation_id=conversation_id,
                        tenant_id=tenant_id,
                        payload=MessagePayload(
                            id=agent_msg.id,
                            role=agent_msg.role.value,
                            sender_type=agent_msg.sender_type,
                            agent_id=user_id,
                            content=agent_msg.content,
                            created_at=agent_msg.created_at,
                        ).model_dump(mode="json"),
                    )
                    await conn_mgr.broadcast_conversation_event(tenant_id, conversation_id, msg_event)

                # 4. Action: Agent Typing Indicator
                elif action == "typing":
                    typing_event = WSEvent(
                        event=WSEventType.TYPING,
                        conversation_id=conversation_id,
                        tenant_id=tenant_id,
                        payload={"is_typing": bool(frame.get("is_typing", True)), "sender": "agent"},
                    )
                    await conn_mgr.broadcast_conversation_event(tenant_id, conversation_id, typing_event)

    except WebSocketDisconnect:
        await conn_mgr.disconnect_agent(tenant_id, user_id, websocket)
    except Exception as exc:
        logger.error("Unhandled error in agent WS: %r", exc)
        await conn_mgr.disconnect_agent(tenant_id, user_id, websocket)


# ==============================================================================
# 2. Visitor WebSocket Gateway: /api/v1/chat/ws/{conversation_id}
# ==============================================================================


@router.websocket("/{conversation_id}")
async def visitor_websocket_endpoint(
    websocket: WebSocket,
    conversation_id: uuid.UUID,
    token: str | None = Query(None),
) -> None:
    """Real-time bi-directional WebSocket gateway for website widget visitors."""
    # 12b HITL
    settings = get_settings()

    # 1. Extract and validate Visitor JWT Session Token
    token = token or websocket.query_params.get("token")
    if not token:
        await websocket.accept()
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing visitor token")
        return

    try:
        payload = decode_visitor_token(token, settings.secret_key.get_secret_value())
        tenant_id = uuid.UUID(payload["tenant_id"])
        visitor_id = str(payload["sub"])
    except Exception as exc:
        logger.warning("Invalid visitor WS auth token for conv %s: %r", conversation_id, exc)
        await websocket.accept()
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid visitor token")
        return

    conn_mgr = get_connection_manager()

    # 2. Connect visitor socket
    await conn_mgr.connect_visitor(tenant_id, conversation_id, websocket)

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                frame: dict[str, Any] = json.loads(raw_text)
            except Exception:
                continue

            frame_type = frame.get("type")

            # Heartbeat ping
            if frame_type == "ping":
                await websocket.send_json({"event": "pong", "timestamp": datetime.now(UTC).isoformat()})
                continue

            # Visitor typing presence
            if frame_type == "typing":
                typing_event = WSEvent(
                    event=WSEventType.TYPING,
                    conversation_id=conversation_id,
                    tenant_id=tenant_id,
                    payload={"is_typing": bool(frame.get("is_typing", True)), "sender": "visitor"},
                )
                await conn_mgr.broadcast_conversation_event(tenant_id, conversation_id, typing_event)
                continue

            # Incoming visitor message
            if frame_type == "message":
                content = str(frame.get("content", "")).strip()
                if not content:
                    continue

                async with get_sessionmaker()() as session:
                    repo = ChatRepository(session)
                    conv = await repo.get_conversation(tenant_id=tenant_id, conversation_id=conversation_id)
                    if not conv:
                        await websocket.send_json({"event": "error", "message": "Conversation not found"})
                        continue

                    # 1. Save visitor message in PostgreSQL
                    visitor_msg = await repo.create_message(
                        tenant_id=tenant_id,
                        conversation_id=conversation_id,
                        role=MessageRole.USER,
                        sender_type=SenderType.VISITOR,
                        content=content,
                    )
                    await session.commit()

                    # Broadcast visitor message to conversation channel
                    msg_event = WSEvent(
                        event=WSEventType.MESSAGE,
                        conversation_id=conversation_id,
                        tenant_id=tenant_id,
                        payload=MessagePayload(
                            id=visitor_msg.id,
                            role=visitor_msg.role.value,
                            sender_type=visitor_msg.sender_type,
                            content=visitor_msg.content,
                            created_at=visitor_msg.created_at,
                        ).model_dump(mode="json"),
                    )
                    await conn_mgr.broadcast_conversation_event(tenant_id, conversation_id, msg_event)

                    # 2. Dispatch based on conversation lifecycle status
                    # CASE A: AI Mode -> Check handoff triggers or stream RAG reply
                    if conv.status == ConversationStatus.AI:
                        if detect_handoff_request(content, conv.metadata_):
                            # Trigger human handoff
                            conv.status = ConversationStatus.HANDOFF_REQUESTED
                            guardrail_msg = await repo.create_message(
                                tenant_id=tenant_id,
                                conversation_id=conversation_id,
                                role=MessageRole.ASSISTANT,
                                sender_type=SenderType.AI,
                                content=HANDOFF_GUARDRAIL_REPLY,
                            )
                            await session.commit()

                            # Broadcast status change to visitor
                            status_event = WSEvent(
                                event=WSEventType.STATUS_CHANGE,
                                conversation_id=conversation_id,
                                tenant_id=tenant_id,
                                payload=StatusChangePayload(status=ConversationStatus.HANDOFF_REQUESTED).model_dump(mode="json"),
                            )
                            await conn_mgr.broadcast_conversation_event(tenant_id, conversation_id, status_event)

                            # Broadcast guardrail message
                            guardrail_event = WSEvent(
                                event=WSEventType.MESSAGE,
                                conversation_id=conversation_id,
                                tenant_id=tenant_id,
                                payload=MessagePayload(
                                    id=guardrail_msg.id,
                                    role=guardrail_msg.role.value,
                                    sender_type=guardrail_msg.sender_type,
                                    content=guardrail_msg.content,
                                    created_at=guardrail_msg.created_at,
                                ).model_dump(mode="json"),
                            )
                            await conn_mgr.broadcast_conversation_event(tenant_id, conversation_id, guardrail_event)

                            # Send high-priority alert to all connected agency agents
                            alert_event = WSEvent(
                                event=WSEventType.HANDOFF_REQUEST,
                                conversation_id=conversation_id,
                                tenant_id=tenant_id,
                                payload={
                                    "visitor_id": visitor_id,
                                    "conversation_title": conv.title or "Visitor Inquiry",
                                    "snippet": content,
                                },
                            )
                            await conn_mgr.broadcast_agent_alert(tenant_id, alert_event)

                        else:
                            # Stream RAG assistant reply
                            retrieval = get_retrieval_service(session, settings)
                            chat_service = ChatService(
                                repository=repo,
                                retrieval=retrieval,
                                llm=websocket.app.state.llm_client or build_llm_client(settings),
                            )

                            accumulated: list[str] = []
                            try:
                                async for token_chunk in chat_service.stream_chat(
                                    tenant_id=tenant_id,
                                    conversation_id=conversation_id,
                                    user_message=content,
                                ):
                                    accumulated.append(token_chunk)
                                    token_event = WSEvent(
                                        event=WSEventType.TOKEN,
                                        conversation_id=conversation_id,
                                        tenant_id=tenant_id,
                                        payload={"token": token_chunk},
                                    )
                                    await conn_mgr.broadcast_conversation_event(tenant_id, conversation_id, token_event)
                            except Exception as llm_exc:
                                logger.error("LLM stream error over WS: %r", llm_exc)
                                err_event = WSEvent(
                                    event=WSEventType.ERROR,
                                    conversation_id=conversation_id,
                                    tenant_id=tenant_id,
                                    payload={"message": "AI assistant response stream interrupted."},
                                )
                                await conn_mgr.broadcast_conversation_event(tenant_id, conversation_id, err_event)

                    # CASE B: Human Active / Handoff Requested -> Forward buyer message directly to live agent
                    elif conv.status in (ConversationStatus.HUMAN_ACTIVE, ConversationStatus.HANDOFF_REQUESTED):
                        buyer_alert = WSEvent(
                            event=WSEventType.MESSAGE,
                            conversation_id=conversation_id,
                            tenant_id=tenant_id,
                            payload=MessagePayload(
                                id=visitor_msg.id,
                                role=visitor_msg.role.value,
                                sender_type=visitor_msg.sender_type,
                                content=visitor_msg.content,
                                created_at=visitor_msg.created_at,
                            ).model_dump(mode="json"),
                        )
                        await conn_mgr.broadcast_agent_alert(tenant_id, buyer_alert)

    except WebSocketDisconnect:
        await conn_mgr.disconnect_visitor(tenant_id, conversation_id, websocket)
    except Exception as exc:
        logger.error("Unhandled error in visitor WS: %r", exc)
        await conn_mgr.disconnect_visitor(tenant_id, conversation_id, websocket)
