from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.bookings.enums import BookingSource, BookingStatus

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.chat.models import Conversation


def _enum_values(enum_cls):
    return [m.value for m in enum_cls]


class ViewingBooking(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "viewing_bookings"
    __table_args__ = (
        Index("ix_vbookings_tenant_status",  "tenant_id", "status"),
        Index("ix_vbookings_tenant_created", "tenant_id", "created_at"),
        Index("ix_vbookings_phone_date",     "phone", "preferred_time"),
    )

    # ── Tenant isolation ────────────────────────────────────────────────────
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # ── Linked conversation (nullable — booking may be created from dashboard) ──
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # ── Agent who will conduct the viewing ──────────────────────────────────
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # ── Visitor contact details ─────────────────────────────────────────────
    visitor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str]        = mapped_column(String(50),  nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Property reference (free-text; Phase 14.3 will add FK once catalog is built) ──
    property_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Appointment slot ────────────────────────────────────────────────────
    preferred_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # ── Lifecycle ───────────────────────────────────────────────────────────
    status: Mapped[BookingStatus] = mapped_column(
        SAEnum(
            BookingStatus,
            native_enum=False,
            length=20,
            values_callable=_enum_values,
        ),
        default=BookingStatus.PENDING,
        server_default=text("'pending'"),
        nullable=False,
        index=True,
    )

    source: Mapped[BookingSource] = mapped_column(
        SAEnum(
            BookingSource,
            native_enum=False,
            length=20,
            values_callable=_enum_values,
        ),
        default=BookingSource.AI_AGENT,
        server_default=text("'ai_agent'"),
        nullable=False,
    )

    # ── Optional agent notes / cancellation reason ──────────────────────────
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ───────────────────────────────────────────────────────
    conversation: Mapped[Conversation | None] = relationship(
        "Conversation",
        foreign_keys=[conversation_id],
        lazy="selectin",
    )
    assigned_agent: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[assigned_agent_id],
        lazy="selectin",
    )