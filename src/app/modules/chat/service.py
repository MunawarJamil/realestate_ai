import logging
import uuid
from collections.abc import AsyncIterator, Sequence
from typing import Any

from app.integrations.llm.base import ChatMessage, LLMProvider
from app.integrations.llm.exceptions import LLMError
from app.modules.chat.enums import MessageRole
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
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Conversation]:
        return await self._repository.list_conversations(
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
        )

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
        await self.get_conversation(tenant_id=tenant_id, conversation_id=conversation_id)

        # 1. Persist user message
        await self._repository.create_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=clean_text,
        )

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

        await self.get_conversation(tenant_id=tenant_id, conversation_id=conversation_id)

        # 1. Persist user message
        await self._repository.create_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=clean_text,
        )

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
