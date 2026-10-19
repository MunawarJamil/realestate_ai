from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.modules.chat.enums import ConversationStatus, SenderType


class ConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)

 
class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str | None
    status: ConversationStatus = ConversationStatus.AI
    assigned_agent_id: uuid.UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime


class ConversationList(BaseModel):
    items: list[ConversationRead]
    total: int


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    tenant_id: uuid.UUID
    role: str
    sender_type: SenderType = SenderType.VISITOR
    agent_id: uuid.UUID | None = None
    content: str
    token_count: int | None = None
    created_at: datetime


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class ConversationStatusUpdateRequest(BaseModel):
    status: ConversationStatus
    assigned_agent_id: uuid.UUID | None = None


class ConversationSummaryResponse(BaseModel):
    conversation_id: uuid.UUID
    summary: str
    key_intent: str | None = None
    budget: str | None = None
    preferred_location: str | None = None
