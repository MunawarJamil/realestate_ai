import logging
import uuid
from collections.abc import AsyncIterator, Sequence
from typing import Any

from app.integrations.llm.base import ChatMessage, LLMProvider
from app.integrations.llm.exceptions import LLMError
from app.modules.chat.enums import ConversationStatus, MessageRole, SenderType
from app.modules.chat.exceptions import (
    ChatServiceUnavailableError,
    ConversationNotFoundError,
    InvalidMessageError,
)
from app.modules.chat.models import Conversation, Message
from app.modules.chat.prompts import build_chat_messages
from app.modules.chat.repository import ChatRepository
from app.modules.knowledge.retrieval import RetrievalService

logger = logging.getLogger(__name__)


class ChatService:
    """Orchestrates conversations, retrieval-augmented prompt assembly, and LLM responses."""

    def __init__(
        self,
        *,
        repository: ChatRepository,
        retrieval: RetrievalService,
        llm: LLMProvider,
    ) -> None:
        self._repository = repository
        self._retrieval = retrieval
        self._llm = llm

    async def create_conversation(
        self,
        *,
        tenant_id: uuid.UUID,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Conversation:
        return await self._repository.create_conversation(
            tenant_id=tenant_id,
            title=title or "New Inquiry",
            metadata=metadata or {},
        )

    async def get_conversation(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> Conversation:
        conversation = await self._repository.get_conversation(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
        )
        if not conversation:
            raise ConversationNotFoundError(
                f"Conversation {conversation_id} not found for this tenant."
            )
        return conversation

    async def list_conversations(
        self,
        *,
        tenant_id: uuid.UUID,
        status: ConversationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Conversation]:
        return await self._repository.list_conversations(
            tenant_id=tenant_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def update_conversation_status(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        status: ConversationStatus,
        assigned_agent_id: uuid.UUID | None = None,
    ) -> Conversation:
        conversation = await self._repository.update_conversation_status(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            status=status,
            assigned_agent_id=assigned_agent_id,
        )
        if not conversation:
            raise ConversationNotFoundError(
                f"Conversation {conversation_id} not found."
            )
        return conversation

    async def list_conversations_for_visitor(
        self,
        *,
        tenant_id: uuid.UUID,
        visitor_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Conversation]:
        return await self._repository.list_conversations_for_visitor(
            tenant_id=tenant_id,
            visitor_id=visitor_id,
            limit=limit,
            offset=offset,
        )

    async def get_conversation_for_visitor(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        visitor_id: str,
    ) -> Conversation:
        conversation = await self._repository.get_conversation_for_visitor(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            visitor_id=visitor_id,
        )
        if not conversation:
            raise ConversationNotFoundError(
                f"Conversation {conversation_id} not found."
            )
        return conversation


    async def list_messages(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Message]:
        # Validate conversation ownership
        await self.get_conversation(tenant_id=tenant_id, conversation_id=conversation_id)
        return await self._repository.list_messages(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            limit=limit,
            offset=offset,
        )

    async def send_message(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        user_message: str,
    ) -> Message:
        clean_text = user_message.strip()
        if not clean_text:
            raise InvalidMessageError("Message content cannot be empty.")

        # Ensure conversation exists
        conv = await self.get_conversation(tenant_id=tenant_id, conversation_id=conversation_id)

        # 1. Persist user message
        user_msg = await self._repository.create_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=clean_text,
        )

        # # 12b HITL - Detect human handoff request in REST mode
        from app.modules.chat.handoff import HANDOFF_GUARDRAIL_REPLY, detect_handoff_request

        if conv.status == ConversationStatus.AI and detect_handoff_request(clean_text, conv.metadata_):
            await self._repository.update_conversation_status(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                status=ConversationStatus.HANDOFF_REQUESTED,
            )
            assistant_message = await self._repository.create_message(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                sender_type=SenderType.AI,
                content=HANDOFF_GUARDRAIL_REPLY,
            )
            try:
                from app.modules.chat.connection_manager import get_connection_manager
                from app.modules.chat.events import (
                    StatusChangePayload,
                    WSEvent,
                    WSEventType,
                )

                conn_mgr = get_connection_manager()
                status_event = WSEvent(
                    event=WSEventType.STATUS_CHANGE,
                    conversation_id=conversation_id,
                    tenant_id=tenant_id,
                    payload=StatusChangePayload(status=ConversationStatus.HANDOFF_REQUESTED).model_dump(mode="json"),
                )
                await conn_mgr.broadcast_conversation_event(tenant_id, conversation_id, status_event)
                await conn_mgr.broadcast_agent_alert(tenant_id, status_event)

                alert_event = WSEvent(
                    event=WSEventType.HANDOFF_REQUEST,
                    conversation_id=conversation_id,
                    tenant_id=tenant_id,
                    payload={
                        "conversation_title": conv.title or "Visitor Inquiry",
                        "snippet": clean_text,
                    },
                )
                await conn_mgr.broadcast_agent_alert(tenant_id, alert_event)
            except Exception as exc:
                logger.warning("Could not broadcast handoff event: %r", exc)
            return assistant_message

        # # 12b HITL - If human agent is already active or handoff is queued, AI agent remains silent!
        if conv.status in (ConversationStatus.HUMAN_ACTIVE, ConversationStatus.HANDOFF_REQUESTED):
            try:
                from app.modules.chat.connection_manager import get_connection_manager
                from app.modules.chat.events import MessagePayload, WSEvent, WSEventType

                conn_mgr = get_connection_manager()
                buyer_alert = WSEvent(
                    event=WSEventType.MESSAGE,
                    conversation_id=conversation_id,
                    tenant_id=tenant_id,
                    payload=MessagePayload(
                        id=user_msg.id,
                        role=user_msg.role.value,
                        sender_type=user_msg.sender_type,
                        content=user_msg.content,
                        created_at=user_msg.created_at,
                    ).model_dump(mode="json"),
                )
                await conn_mgr.broadcast_agent_alert(tenant_id, buyer_alert)
            except Exception as exc:
                logger.warning("Could not broadcast buyer message in HITL mode: %r", exc)
            return user_msg

        # 2. Build history (excluding the current turn which we just added)
        history_records = await self._repository.get_recent_messages(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            limit=11,
        )
        history = [
            ChatMessage(role=msg.role.value, content=msg.content)
            for msg in history_records[:-1]
        ]

        # 3. Retrieve relevant chunks
        try:
            chunks = await self._retrieval.search(tenant_id=tenant_id, query=clean_text)
        except Exception as exc:
            logger.warning("Knowledge retrieval failed for chat: %r", exc)
            chunks = []

        # 4. Assemble prompt
        prompt_messages = build_chat_messages(
            user_query=clean_text,
            context_chunks=chunks,
            history=history,
        )

        # 5. Call LLM
        try:
            response = await self._llm.complete(prompt_messages)
        except LLMError as exc:
            logger.error("LLM completion failed: %r", exc)
            raise ChatServiceUnavailableError("AI response generation unavailable.") from exc

        # 6. Save assistant message
        assistant_message = await self._repository.create_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=response.content,
            token_count=response.completion_tokens,
        )
        return assistant_message

    async def stream_chat(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        user_message: str,
    ) -> AsyncIterator[str]:
        clean_text = user_message.strip()
        if not clean_text:
            raise InvalidMessageError("Message content cannot be empty.")

        conv = await self.get_conversation(tenant_id=tenant_id, conversation_id=conversation_id)

        # 1. Persist user message
        user_msg = await self._repository.create_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=clean_text,
        )

        # # 12b HITL - Detect human handoff request in stream mode
        from app.modules.chat.handoff import HANDOFF_GUARDRAIL_REPLY, detect_handoff_request

        if conv.status == ConversationStatus.AI and detect_handoff_request(clean_text, conv.metadata_):
            await self._repository.update_conversation_status(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                status=ConversationStatus.HANDOFF_REQUESTED,
            )
            await self._repository.create_message(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                sender_type=SenderType.AI,
                content=HANDOFF_GUARDRAIL_REPLY,
            )
            try:
                from app.modules.chat.connection_manager import get_connection_manager
                from app.modules.chat.events import (
                    StatusChangePayload,
                    WSEvent,
                    WSEventType,
                )

                conn_mgr = get_connection_manager()
                status_event = WSEvent(
                    event=WSEventType.STATUS_CHANGE,
                    conversation_id=conversation_id,
                    tenant_id=tenant_id,
                    payload=StatusChangePayload(status=ConversationStatus.HANDOFF_REQUESTED).model_dump(mode="json"),
                )
                await conn_mgr.broadcast_conversation_event(tenant_id, conversation_id, status_event)
                await conn_mgr.broadcast_agent_alert(tenant_id, status_event)

                alert_event = WSEvent(
                    event=WSEventType.HANDOFF_REQUEST,
                    conversation_id=conversation_id,
                    tenant_id=tenant_id,
                    payload={
                        "conversation_title": conv.title or "Visitor Inquiry",
                        "snippet": clean_text,
                    },
                )
                await conn_mgr.broadcast_agent_alert(tenant_id, alert_event)
            except Exception as exc:
                logger.warning("Could not broadcast handoff event from stream_chat: %r", exc)

            for token in HANDOFF_GUARDRAIL_REPLY.split(" "):
                yield token + " "
            return

        # # 12b HITL - If human agent is already active or handoff is queued, AI agent remains silent!
        if conv.status in (ConversationStatus.HUMAN_ACTIVE, ConversationStatus.HANDOFF_REQUESTED):
            try:
                from app.modules.chat.connection_manager import get_connection_manager
                from app.modules.chat.events import MessagePayload, WSEvent, WSEventType

                conn_mgr = get_connection_manager()
                buyer_alert = WSEvent(
                    event=WSEventType.MESSAGE,
                    conversation_id=conversation_id,
                    tenant_id=tenant_id,
                    payload=MessagePayload(
                        id=user_msg.id,
                        role=user_msg.role.value,
                        sender_type=user_msg.sender_type,
                        content=user_msg.content,
                        created_at=user_msg.created_at,
                    ).model_dump(mode="json"),
                )
                await conn_mgr.broadcast_agent_alert(tenant_id, buyer_alert)
            except Exception as exc:
                logger.warning("Could not broadcast buyer message in HITL mode: %r", exc)
            return

        # 2. Fetch history
        history_records = await self._repository.get_recent_messages(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            limit=11,
        )
        history = [
            ChatMessage(role=msg.role.value, content=msg.content)
            for msg in history_records[:-1]
        ]

        # 3. Retrieve knowledge
        try:
            chunks = await self._retrieval.search(tenant_id=tenant_id, query=clean_text)
        except Exception as exc:
            logger.warning("Knowledge retrieval failed for chat stream: %r", exc)
            chunks = []

        # 4. Build prompt
        prompt_messages = build_chat_messages(
            user_query=clean_text,
            context_chunks=chunks,
            history=history,
        )

        # 5. Stream tokens and accumulate for DB persistence
        accumulated: list[str] = []
        try:
            async for token in self._llm.stream(prompt_messages):
                accumulated.append(token)
                yield token
        except LLMError as exc:
            logger.error("LLM stream failed: %r", exc)
            raise ChatServiceUnavailableError("AI streaming generation unavailable.") from exc

        # 6. Persist final assistant response
        final_content = "".join(accumulated).strip()
        if final_content:
            await self._repository.create_message(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=final_content,
            )

    # 12b HITL - Agent Claim Conversation
    async def claim_conversation(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        agent_id: uuid.UUID,
        agent_name: str | None = None,
    ) -> Conversation:
        conversation = await self.get_conversation(tenant_id=tenant_id, conversation_id=conversation_id)
        conversation.status = ConversationStatus.HUMAN_ACTIVE
        conversation.assigned_agent_id = agent_id

        # Insert audit system message
        name = agent_name or "A licensed property advisor"
        await self._repository.create_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=MessageRole.SYSTEM,
            sender_type=SenderType.SYSTEM,
            agent_id=agent_id,
            content=f"{name} has joined the conversation.",
        )

        # Broadcast real-time status update to visitor & agent alert room
        try:
            from app.modules.chat.connection_manager import get_connection_manager
            from app.modules.chat.events import StatusChangePayload, WSEvent, WSEventType

            conn_mgr = get_connection_manager()
            event = WSEvent(
                event=WSEventType.STATUS_CHANGE,
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                payload=StatusChangePayload(
                    status=ConversationStatus.HUMAN_ACTIVE,
                    assigned_agent_id=agent_id,
                ).model_dump(mode="json"),
            )
            await conn_mgr.broadcast_conversation_event(tenant_id, conversation_id, event)
            await conn_mgr.broadcast_agent_alert(tenant_id, event)
        except Exception as exc:
            logger.warning("Failed to broadcast claim event to Redis: %r", exc)

        await self._repository._session.flush()
        await self._repository._session.refresh(conversation)
        return conversation

    # 12b HITL - Agent Release Conversation back to AI
    async def release_conversation(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> Conversation:
        conversation = await self.get_conversation(tenant_id=tenant_id, conversation_id=conversation_id)
        conversation.status = ConversationStatus.AI
        conversation.assigned_agent_id = None

        await self._repository.create_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=MessageRole.SYSTEM,
            sender_type=SenderType.SYSTEM,
            content="Conversation returned to AI assistant.",
        )

        try:
            from app.modules.chat.connection_manager import get_connection_manager
            from app.modules.chat.events import StatusChangePayload, WSEvent, WSEventType

            conn_mgr = get_connection_manager()
            event = WSEvent(
                event=WSEventType.STATUS_CHANGE,
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                payload=StatusChangePayload(
                    status=ConversationStatus.AI,
                    assigned_agent_id=None,
                ).model_dump(mode="json"),
            )
            await conn_mgr.broadcast_conversation_event(tenant_id, conversation_id, event)
            await conn_mgr.broadcast_agent_alert(tenant_id, event)
        except Exception as exc:
            logger.warning("Failed to broadcast release event to Redis: %r", exc)

        await self._repository._session.flush()
        await self._repository._session.refresh(conversation)
        return conversation

    # 12b HITL - Resolve Conversation
    async def resolve_conversation(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> Conversation:
        conversation = await self.get_conversation(tenant_id=tenant_id, conversation_id=conversation_id)
        conversation.status = ConversationStatus.RESOLVED

        await self._repository.create_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=MessageRole.SYSTEM,
            sender_type=SenderType.SYSTEM,
            content="Conversation marked as resolved.",
        )

        try:
            from app.modules.chat.connection_manager import get_connection_manager
            from app.modules.chat.events import StatusChangePayload, WSEvent, WSEventType

            conn_mgr = get_connection_manager()
            event = WSEvent(
                event=WSEventType.STATUS_CHANGE,
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                payload=StatusChangePayload(
                    status=ConversationStatus.RESOLVED,
                    assigned_agent_id=conversation.assigned_agent_id,
                ).model_dump(mode="json"),
            )
            await conn_mgr.broadcast_conversation_event(tenant_id, conversation_id, event)
            await conn_mgr.broadcast_agent_alert(tenant_id, event)
        except Exception as exc:
            logger.warning("Failed to broadcast resolve event to Redis: %r", exc)

        await self._repository._session.flush()
        await self._repository._session.refresh(conversation)
        return conversation

    # 12b HITL - AI Handover Summary Generator
    async def summarize_conversation(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ):
        import json
        from app.modules.chat.prompts import build_summary_messages
        from app.modules.chat.schemas import ConversationSummaryResponse

        # 1. Fetch conversation and messages
        await self.get_conversation(tenant_id=tenant_id, conversation_id=conversation_id)
        messages = await self._repository.list_messages(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            limit=50,
            offset=0,
        )

        # Filter meaningful visitor/assistant dialogue
        dialogue = [m for m in messages if m.role in ("user", "assistant") and m.content.strip()]
        if len(dialogue) < 2:
            return ConversationSummaryResponse(
                conversation_id=conversation_id,
                summary="New inquiry with minimal interaction. Client has not specified detailed requirements yet.",
                key_intent="General Inquiry",
                budget=None,
                preferred_location=None,
            )

        chat_history = [ChatMessage(role=m.role, content=m.content) for m in dialogue]
        prompt = build_summary_messages(chat_history)

        try:
            llm_response = await self._llm.complete(prompt)
            clean_text = llm_response.content.strip()
            # Clean markdown code blocks if model included any
            if clean_text.startswith("```"):
                lines = clean_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                clean_text = "\n".join(lines).strip()

            parsed = json.loads(clean_text)
            return ConversationSummaryResponse(
                conversation_id=conversation_id,
                summary=parsed.get("summary") or "Inquiry underway.",
                key_intent=parsed.get("key_intent"),
                budget=parsed.get("budget"),
                preferred_location=parsed.get("preferred_location"),
            )
        except Exception as exc:
            logger.warning("LLM summary generation failed: %r", exc)
            return ConversationSummaryResponse(
                conversation_id=conversation_id,
                summary="Inquiry regarding real estate properties. Ready for broker assistance.",
                key_intent="Property Consultation",
                budget=None,
                preferred_location=None,
            )

