from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.modules.bookings.enums import BookingSource, BookingStatus


# ── Constants ───────────────────────────────────────────────────────────────

_PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")


# ── Shared base ─────────────────────────────────────────────────────────────

class BookingBase(BaseModel):
    visitor_name: str         = Field(..., min_length=1, max_length=255)
    phone: str                = Field(..., min_length=7,  max_length=50)
    email: EmailStr | None    = Field(default=None)
    property_ref: str | None  = Field(default=None, max_length=500,
                                       description="Free-text property identifier (address, title, or ID)")
    preferred_time: datetime  = Field(..., description="Desired viewing datetime (timezone-aware UTC)")
    notes: str | None         = Field(default=None)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.strip()
        if not _PHONE_RE.match(cleaned):
            raise ValueError("phone must be 7-15 digits, optionally prefixed with '+'")
        return cleaned

    @field_validator("preferred_time")
    @classmethod
    def validate_preferred_time(cls, v: datetime) -> datetime:
        # Normalise to UTC if naive
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= datetime.now(timezone.utc):
            raise ValueError("preferred_time must be in the future")
        return v


# ── Create 

class BookingCreate(BookingBase):
    conversation_id: uuid.UUID | None  = Field(default=None)
    assigned_agent_id: uuid.UUID | None = Field(default=None)
    source: BookingSource              = Field(default=BookingSource.AI_AGENT)


# ── Update (all fields optional) ─────────────────────────────────────────────

class BookingUpdate(BaseModel):
    visitor_name: str | None      = Field(default=None, max_length=255)
    phone: str | None             = Field(default=None, max_length=50)
    email: EmailStr | None        = None
    property_ref: str | None      = Field(default=None, max_length=500)
    preferred_time: datetime | None = None
    status: BookingStatus | None  = None
    assigned_agent_id: uuid.UUID | None = None
    notes: str | None             = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        cleaned = v.strip()
        if not _PHONE_RE.match(cleaned):
            raise ValueError("phone must be 7–15 digits, optionally prefixed with '+'")
        return cleaned

    @field_validator("preferred_time")
    @classmethod
    def validate_preferred_time(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= datetime.now(timezone.utc):
            raise ValueError("preferred_time must be in the future")
        return v

    @model_validator(mode="after")
    def at_least_one_field(self) -> BookingUpdate:
        if all(
            getattr(self, f) is None
            for f in self.model_fields
        ):
            raise ValueError("At least one field must be provided for update")
        return self


# ── Read (ORM output) ────────────────────────────────────────────────────────

class BookingRead(BookingBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    conversation_id: uuid.UUID | None
    assigned_agent_id: uuid.UUID | None
    status: BookingStatus
    source: BookingSource
    created_at: datetime
    updated_at: datetime


# ── Paginated list ────────────────────────────────────────────────────────────

class BookingListResponse(BaseModel):
    items: list[BookingRead]
    total: int
    page: int
    size: int
    pages: int


# ── Lightweight tool result  
class BookingConfirmation(BaseModel):
    """Compact result the AI tool returns to the LangGraph node."""
    booking_id: uuid.UUID
    status: BookingStatus
    visitor_name: str
    preferred_time: datetime
    confirmation_message: str   # Human-readable message to relay back to the visitor