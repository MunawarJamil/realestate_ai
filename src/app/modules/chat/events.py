# 12b HITL - WebSocket & PubSub Event Schemas
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.modules.chat.enums import ConversationStatus, SenderType


class WSEventType(StrEnum):
    """Event types exchanged over WebSockets and Redis pub/sub."""
    # 12b HITL
    TOKEN = "token"                   # AI streaming token chunk
    MESSAGE = "message"               # Full committed message
    STATUS_CHANGE = "status_change"   # Lifecycle state transition
    HANDOFF_REQUEST = "handoff_request" # Alert to agency agents
    AGENT_CLAIMED = "agent_claimed"   # Agent took ownership
    AGENT_RELEASED = "agent_released" # Agent released back to AI
    TYPING = "typing"                 # Typing indicator
    PRESENCE = "presence"             # Online/offline presence
    ERROR = "error"                   # Error details
    PING = "ping"                     # Heartbeat ping
    PONG = "pong"                     # Heartbeat pong


class WSEvent(BaseModel):
    """Standard envelope for all real-time events."""
    # 12b HITL
    model_config = ConfigDict(from_attributes=True)

    event: WSEventType
    conversation_id: uuid.UUID
    tenant_id: uuid.UUID
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MessagePayload(BaseModel):
    """Payload for committed messages."""
    # 12b HITL
    id: uuid.UUID
    role: str
    sender_type: SenderType
    content: str
    agent_id: uuid.UUID | None = None
    created_at: datetime


class StatusChangePayload(BaseModel):
    """Payload for conversation lifecycle status updates."""
    # 12b HITL
    status: ConversationStatus
    assigned_agent_id: uuid.UUID | None = None
    agent_name: str | None = None
