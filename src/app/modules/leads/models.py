from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.leads.enums import LeadIntent, LeadStatus

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.chat.models import Conversation


def _enum_values(enum_cls: Any) -> list[str]:
    return [m.value for m in enum_cls]


class Lead(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_tenant_status", "tenant_id", "status"),
        Index("ix_leads_tenant_ai_score", "tenant_id", "ai_score"),
        Index("ix_leads_tenant_created", "tenant_id", "created_at"),
        CheckConstraint("ai_score >= 0 AND ai_score <= 100", name="ck_leads_ai_score_range"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # Contact Details
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)

    # Real Estate Intent & Preferences
    intent: Mapped[LeadIntent] = mapped_column(
        SAEnum(
            LeadIntent,
            native_enum=False,
            length=30,
            values_callable=_enum_values,
        ),
        default=LeadIntent.BUY,
        server_default=text("'buy'"),
        nullable=False,
    )
    property_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # villa, apartment, townhouse
    preferred_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timeline: Mapped[str | None] = mapped_column(String(100), nullable=True)  # immediate, 1-3 months, flexible

    # Financial Budget Constraints
    budget_min: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    budget_max: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="AED", server_default=text("'AED'"), nullable=False)

    # CRM Lifecycle & AI Auto-Qualification
    status: Mapped[LeadStatus] = mapped_column(
        SAEnum(
            LeadStatus,
            native_enum=False,
            length=30,
            values_callable=_enum_values,
        ),
        default=LeadStatus.NEW,
        server_default=text("'new'"),
        nullable=False,
        index=True,
    )
    ai_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
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
