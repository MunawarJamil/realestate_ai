# 12d HITL - Production-Grade LangGraph State Schema
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, NotRequired, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
 
# Type Aliases

# Named GraphStatus to avoid clashing with chat.enums.ConversationStatus.
# Keep these values in sync with the DB enum (DB is the source of truth).
GraphStatus = Literal[
    "ai",                  # AI is handling the conversation
    "handoff_requested",   # Waiting for a human
    "human_active",        # Human has taken over, AI must stay silent
    "resolved",            # Conversation finished
]

HandoffReason = Literal[
    "user_request",
    "guardrail_trigger",
    "ai_failure",
    "agent_initiated",
    "timeout",
]

# Replace or add the IntentType literal:
IntentType = Literal[
    "greeting",
    "smalltalk",
    "property_inquiry",
    "tool_action",
    "handoff_requested",
    "live_human_support",
]


ConversationChannel = Literal["web", "mobile", "whatsapp", "email"]


# Helpers
def utc_now_iso() -> str:
    """Current UTC time as an ISO-8601 string (use this in nodes)."""
    return datetime.now(UTC).isoformat()


def merge_dicts(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    """Reducer: merge metadata dicts so nodes don't overwrite each other's keys."""
    return {**(left or {}), **(right or {})}


# ==============================================================================
# Core State Schema
# ==============================================================================


class AgentState(TypedDict):
    """State tracked across LangGraph execution turns for a conversation."""
    handoff_notice_sent: NotRequired[bool] 
    # 1. Message history (append-only)
    messages: Annotated[list[BaseMessage], add_messages]

    # 2. Identity (required on first invoke)
    conversation_id: str          # Also used as LangGraph `thread_id`
    tenant_id: str
    channel: ConversationChannel

    # 3. Lifecycle & assignment
    status: GraphStatus
    assigned_agent_id: NotRequired[str | None]

    # 4. Routing & HITL evaluation
    requires_human: NotRequired[bool]
    intent: NotRequired[str | None]
    handoff_reason: NotRequired[HandoffReason | None]
    handoff_requested_at: NotRequired[str | None]      # ISO-8601 UTC
    last_human_activity_at: NotRequired[str | None]    # ISO-8601 UTC
    ai_failure_count: NotRequired[int]                 # Drives the "timeout"/"ai_failure" handoff

    # 5. Grounded RAG context (per-turn)
    context_chunks: NotRequired[list[str]]
    retrieval_failed: NotRequired[bool]

    # 6. Assistant output (per-turn)
    reply_content: NotRequired[str | None]

    # 7. Free-form metadata (merged, not overwritten)
    metadata: Annotated[NotRequired[dict[str, Any]], merge_dicts]
    # 8. Agentic Tool Calling  
    tool_calls: NotRequired[list[dict[str, Any]]]
    tool_results: NotRequired[list[dict[str, Any]]]
 
 
 # Factories 

def make_initial_state(
    *,
    conversation_id: str | uuid.UUID,
    tenant_id: str | uuid.UUID,
    channel: ConversationChannel = "web",
    first_user_message: BaseMessage | None = None,
    metadata: dict[str, Any] | None = None,
) -> AgentState:
    """
    Build the state for a NEW conversation only.

    Do NOT call this on every turn: it sets status="ai" and would reset a
    `human_active` conversation. Use `make_turn_input` for later turns.

    Only required fields plus a few explicit defaults are set; everything else
    is filled in by nodes.
    """
    return AgentState(
        messages=[first_user_message] if first_user_message else [],
        conversation_id=str(conversation_id),
        tenant_id=str(tenant_id),
        channel=channel,
        status="ai",
        ai_failure_count=0,
        metadata=metadata or {},
    )

def make_turn_input(
    *,
    message: BaseMessage,
    status: GraphStatus,
    assigned_agent_id: str | uuid.UUID | None = None,
) -> dict[str, Any]:
    return {
        "messages": [message],
        "status": status,
        "assigned_agent_id": str(assigned_agent_id) if assigned_agent_id else None,
        # Per-turn resets
        "intent": None,
        "requires_human": False,
        "retrieval_failed": False,
        "context_chunks": [],
        "reply_content": None,
        "tool_calls": [],
        "tool_results": [],
    }


# Public exports
__all__ = [
    "AgentState",
    "GraphStatus",
    "HandoffReason",
    "ConversationChannel",
    "make_initial_state",
    "make_turn_input",
    "merge_dicts",
    "utc_now_iso",
]