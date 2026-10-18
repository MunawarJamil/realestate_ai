class ChatError(Exception):
    """Base exception for chat domain."""


class ConversationNotFoundError(ChatError):
    """Raised when a requested conversation is not found for the given tenant."""


class InvalidMessageError(ChatError):
    """Raised when message content is blank or invalid."""


class ChatServiceUnavailableError(ChatError):
    """Raised when an external dependency (LLM or retrieval) is unavailable."""
