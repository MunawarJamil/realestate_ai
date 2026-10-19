from enum import StrEnum


class MessageRole(StrEnum):
    """Roles for LLM message context."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

# 12b HITL
class ConversationStatus(StrEnum):
    """Lifecycle status of a chat session."""
    AI = "ai"
    HANDOFF_REQUESTED = "handoff_requested"
    HUMAN_ACTIVE = "human_active"
    RESOLVED = "resolved"

# 12b HITL
class SenderType(StrEnum):
    """Identifies the origin of a message in a hybrid AI/Human conversation."""
    VISITOR = "visitor"
    AI = "ai"
    AGENT = "agent"
    SYSTEM = "system"
