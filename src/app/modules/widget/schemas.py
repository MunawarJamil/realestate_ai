"""Pydantic schemas for the embeddable chat widget."""

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class WidgetSessionInitRequest(BaseModel):
    """Optional request body when initializing a widget session.

    If the visitor already has a visitor_id saved in client localStorage, they can pass it
    here to resume their conversation history under the verified visitor session token.
    """

    visitor_id: uuid.UUID | None = Field(
        default=None,
        description="Optional existing visitor UUID to resume previous session",
    )


class WidgetSessionResponse(BaseModel):
    """Session credentials returned upon successful widget initialization."""

    model_config = ConfigDict(from_attributes=True)

    visitor_token: str = Field(description="JWT Bearer token to authorize public widget requests")
    visitor_id: uuid.UUID = Field(description="Unique visitor identifier")
    tenant_id: uuid.UUID = Field(description="Tenant ID this widget belongs to")
    tenant_name: str = Field(description="Public display name of the tenant agency")
    expires_at: datetime = Field(description="UTC timestamp when the visitor token expires")


class VisitorContextRead(BaseModel):
    """Verified visitor context schema."""

    model_config = ConfigDict(from_attributes=True)

    visitor_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
