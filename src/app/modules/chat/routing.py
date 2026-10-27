import re
from enum import StrEnum


class QueryIntent(StrEnum):
    CHITCHAT = "chitchat"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"



# Common conversational pleasantries across English, Arabic, and Roman Urdu
_GREETINGS = {
    "hi",
    "hello",
    "hey",
    "hey there",
    "hiya",
    "good morning",
    "good afternoon",
    "good evening",
    "good day",
    "howdy",
    "salam",
    "assalam",
    "assalamu alaikum",
    "asalam alaikum",
    "marhaban",
    "ahlan",
    "ahlan wa sahlan",
    "namaste",
    "adaab",
}

_COURTESIES = {
    "thanks",
    "thank you",
    "thank you so much",
    "thx",
    "great",
    "perfect",
    "awesome",
    "ok",
    "okay",
    "got it",
    "shukran",
    "jazakallah",
    "bye",
    "goodbye",
    "see you",
}

_IDENTITY_PATTERNS = [
    r"^who\s+are\s+you\??$",
    r"^what\s+(is\s+your\s+name|can\s+you\s+do)\??$",
    r"^how\s+can\s+you\s+help\s+me\??$",
    r"^(tell\s+me\s+about\s+yourself|introduce\s+yourself)\??$",
    r"^من\s+أنت[؟?]?$",
    r"^kaun\s+ho\s+tum\??$",
]


# Real estate keywords: if present, never treat as chit-chat even if it begins with a greeting
_REAL_ESTATE_KEYWORDS = re.compile(
    r"\b(price|pricing|cost|aed|usd|\$|villa|apartment|flat|studio|penthouse|"
    r"bedroom|bed|bhk|sqft|payment|plan|down\s*payment|installment|handover|"
    r"amenities|location|developer|viewing|tour|marina|downtown|creek|palm|"
    r"damac|emaar|sobha|aldar|nakheel|property|properties|listing|project)\b",
    re.IGNORECASE | re.UNICODE,
)

_COMPILED_IDENTITY = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in _IDENTITY_PATTERNS]


def should_skip_retrieval(user_query: str) -> bool:
    """Returns True if the message is pure chit-chat, greeting, or identity inquiry.

    Executes in <0.1ms using deterministic pattern matching. If any property-related
    term is detected, returns False to ensure knowledge retrieval is triggered.
    """
    cleaned = user_query.strip().lower()
    if not cleaned:
        return True

    # 1. If any property or commercial keyword is mentioned, ALWAYS retrieve
    if _REAL_ESTATE_KEYWORDS.search(cleaned):
        return False

    # 2. Check exact matches for greetings and courtesies (ignoring trailing punctuation)
    normalized = re.sub(r"[^\w\s]", "", cleaned).strip()
    if normalized in _GREETINGS or normalized in _COURTESIES:
        return True

    # 3. Check assistant identity questions
    return any(pattern.match(cleaned) for pattern in _COMPILED_IDENTITY)

