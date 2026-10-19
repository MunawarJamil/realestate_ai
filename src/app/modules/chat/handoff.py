# 12b HITL - Handoff Trigger Detection & Guardrails
import re
from typing import Any

# 12b HITL - Multi-lingual handoff trigger patterns
_HANDOFF_TRIGGER_PATTERNS = [
    # English
    r"\b(talk|speak|connect|transfer)\b.*\b(human|agent|person|representative|specialist|broker|consultant|advisor)\b",
    r"\b(real\s+person|human\s+agent|live\s+agent|someone\s+else|call\s+me|contact\s+me)\b",
    r"\b(book|schedule)\b.*\b(viewing|tour|visit|appointment)\b",
    # Urdu / Hindi Roman
    r"\b(agent|insan|banday|broker)\b.*\b(baat|connect|call)\b",
    r"\b(kisi\s+se\s+baat|human\s+se\s+baat|agent\s+chahiye|call\s+karo)\b",
    # Arabic
    r"(تحدث|اتصال|تواصل).*(موظف|وكيل|إنسان|شخص|مستشار)",
    r"(حجز|معاينة|زيارة).*(فيلا|شقة|عقار)",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in _HANDOFF_TRIGGER_PATTERNS]

# 12b HITL - Standard guardrail response when AI hands over to human
HANDOFF_GUARDRAIL_REPLY = (
    "I'm connecting you with one of our licensed property advisors right now. "
    "Please hold on for a moment while they join our live chat."
)


# 12b HITL
def detect_handoff_request(message_content: str, metadata: dict[str, Any] | None = None) -> bool:
    """Evaluates whether visitor message expresses a desire to talk to a human agent."""
    cleaned = message_content.strip()
    if not cleaned:
        return False

    for pattern in _COMPILED_PATTERNS:
        if pattern.search(cleaned):
            return True

    # Check metadata intent if extracted by NLP/CRM
    if metadata:
        intent = str(metadata.get("intent", "")).lower()
        if "agent" in intent or "handoff" in intent or "viewing_request" in intent:
            return True

    return False
