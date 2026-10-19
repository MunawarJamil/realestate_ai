from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.auth.models import User  # 12b HITL
from app.modules.chat.enums import ConversationStatus, MessageRole, SenderType


def _enum_values(enum_cls: Any) -> list[str]:
    return [m.value for m in enum_cls]


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_tenant_status", "tenant_id", "status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[ConversationStatus] = mapped_column(
        SAEnum(
            ConversationStatus,
            native_enum=False,
            length=30,
            values_callable=_enum_values,
        ),
        default=ConversationStatus.AI,
        server_default=text("'ai'"),
        nullable=False,
        index=True,
    )

    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )

    assigned_agent: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[assigned_agent_id],
        lazy="selectin",
    )

    messages: Mapped[list[Message]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
# 12b HITL

class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index(
            "ix_messages_tenant_conversation_created",
            "tenant_id",
            "conversation_id",
            "created_at",
        ),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    role: Mapped[MessageRole] = mapped_column(
        SAEnum(
            MessageRole,
            native_enum=False,
            length=20,
            values_callable=_enum_values,
        ),
        nullable=False,
    )

    sender_type: Mapped[SenderType] = mapped_column(
        SAEnum(
            SenderType,
            native_enum=False,
            length=20,
            values_callable=_enum_values,
        ),
        default=SenderType.VISITOR,
        server_default=text("'visitor'"),
        nullable=False,
        index=True,
    )

    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    agent: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[agent_id],
        lazy="selectin",
    )

    conversation: Mapped[Conversation] = relationship(
        "Conversation",
        back_populates="messages",
    )
