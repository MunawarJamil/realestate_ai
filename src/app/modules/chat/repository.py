import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.enums import MessageRole
from app.modules.chat.models import Conversation, Message


class ChatRepository:
    """Async database operations for conversations and messages scoped by tenant_id."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_conversation(
        self,
        *,
        tenant_id: uuid.UUID,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Conversation:
        conversation = Conversation(
            tenant_id=tenant_id,
            title=title,
            metadata_=metadata or {},
        )
        self._session.add(conversation)
        await self._session.flush()
        return conversation

    async def get_conversation(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> Conversation | None:
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_conversations(
        self,
        *,
        tenant_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.tenant_id == tenant_id)
            .order_by(desc(Conversation.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_conversations_for_visitor(
        self,
        *,
        tenant_id: uuid.UUID,
        visitor_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Conversation]:
        stmt = (
            select(Conversation)
            .where(
                Conversation.tenant_id == tenant_id,
                Conversation.metadata_["visitor_id"].astext == visitor_id,
            )
            .order_by(desc(Conversation.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_conversation_for_visitor(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        visitor_id: str,
    ) -> Conversation | None:
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_id,
            Conversation.metadata_["visitor_id"].astext == visitor_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()



    async def delete_conversation(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> bool:
        stmt = (
            delete(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id,
            )
            .returning(Conversation.id)
        )
        deleted_id = (await self._session.execute(stmt)).scalar_one_or_none()
        return deleted_id is not None




    async def create_message(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        role: MessageRole,
        content: str,
        token_count: int | None = None,
    ) -> Message:
        message = Message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            token_count=token_count,
        )
        self._session.add(message)
        await self._session.flush()
        return message

    async def list_messages(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Message]:
        stmt = (
            select(Message)
            .where(
                Message.tenant_id == tenant_id,
                Message.conversation_id == conversation_id,
            )
            .order_by(Message.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_recent_messages(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        limit: int = 10,
    ) -> list[Message]:
        """Fetch the most recent N messages in chronological order."""
        stmt = (
            select(Message)
            .where(
                Message.tenant_id == tenant_id,
                Message.conversation_id == conversation_id,
            )
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        messages = list(result.scalars().all())
        messages.reverse()
        return messages
