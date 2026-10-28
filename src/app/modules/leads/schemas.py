from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field

from app.modules.leads.enums import LeadIntent, LeadScoreCategory, LeadStatus


class LeadScoreBreakdown(BaseModel):
    """Structured breakdown explaining the lead qualification score."""
    model_config = ConfigDict(extra="allow")

    budget_score: int = Field(default=0, ge=0, le=30, description="Max 30 pts for defined budget")
    timeline_score: int = Field(default=0, ge=0, le=25, description="Max 25 pts for urgent/clear timeline")
    intent_score: int = Field(default=0, ge=0, le=25, description="Max 25 pts for high intent (buy/invest)")
    contact_score: int = Field(default=0, ge=0, le=20, description="Max 20 pts for phone/email provided")
    rationale: str = Field(default="", description="LLM concise explanation of the assigned score")


class LeadBase(BaseModel):
    contact_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    intent: LeadIntent = Field(default=LeadIntent.BUY)
    property_type: str | None = Field(default=None, max_length=100)
    preferred_location: str | None = Field(default=None, max_length=255)
    timeline: str | None = Field(default=None, max_length=100)
    budget_min: Decimal | None = Field(default=None)
    budget_max: Decimal | None = Field(default=None)
    currency: str = Field(default="AED", max_length=10)
    notes: str | None = None


class LeadCreate(LeadBase):
    conversation_id: uuid.UUID | None = None
    assigned_agent_id: uuid.UUID | None = None
    status: LeadStatus = LeadStatus.NEW
    ai_score: int = Field(default=0, ge=0, le=100)
    score_breakdown: dict[str, Any] = Field(default_factory=dict)


class LeadUpdate(BaseModel):
    contact_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    intent: LeadIntent | None = None
    property_type: str | None = Field(default=None, max_length=100)
    preferred_location: str | None = Field(default=None, max_length=255)
    timeline: str | None = Field(default=None, max_length=100)
    budget_min: Decimal | None = Field(default=None)
    budget_max: Decimal | None = Field(default=None)
    currency: str | None = Field(default=None, max_length=10)
    status: LeadStatus | None = None
    assigned_agent_id: uuid.UUID | None = None
    ai_score: int | None = Field(default=None, ge=0, le=100)
    score_breakdown: dict[str, Any] | None = None
    notes: str | None = None


class LeadRead(LeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    conversation_id: uuid.UUID | None
    assigned_agent_id: uuid.UUID | None
    status: LeadStatus
    ai_score: int
    score_breakdown: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def score_category(self) -> LeadScoreCategory:
        if self.ai_score >= 85:
            return LeadScoreCategory.HOT
        if self.ai_score >= 70:
            return LeadScoreCategory.WARM
        return LeadScoreCategory.COLD


class LeadListResponse(BaseModel):
    items: list[LeadRead]
    total: int
    page: int
    size: int
    pages: int
