import pytest

from app.modules.chat.routing import should_skip_retrieval


@pytest.mark.parametrize(
    "query",
    [
        "hi",
        "Hi",
        "HELLO!",
        "hey there",
        "good morning",
        "good afternoon",
        "good evening",
        "salam",
        "Assalamu Alaikum",
        "asalam alaikum",
        "marhaban",
        "ahlan wa sahlan",
        "namaste",
        "thanks",
        "Thank you so much!",
        "thx",
        "ok",
        "okay",
        "perfect",
        "shukran",
        "jazakallah",
        "bye",
        "goodbye",
    ],
)
def test_pure_greetings_and_courtesies_skip_retrieval(query: str) -> None:
    assert should_skip_retrieval(query) is True


@pytest.mark.parametrize(
    "query",
    [
        "who are you?",
        "Who are you",
        "what can you do?",
        "how can you help me?",
        "tell me about yourself",
        "introduce yourself",
        "من أنت؟",
        "kaun ho tum?",
    ],
)
def test_identity_inquiries_skip_retrieval(query: str) -> None:
    assert should_skip_retrieval(query) is True


@pytest.mark.parametrize(
    "query",
    [
        "What is the price of the 2-bedroom apartment?",
        "Do you have villas available in Dubai Marina?",
        "What is the down payment and payment plan for Lotus?",
        "Tell me about Emaar beachfront projects.",
        "How many sqft is the penthouse?",
        "Are there 3 BHK units under 2M AED?",
        "When is the handover date?",
        "What are the amenities included in Sobha Hartland?",
        "Can I schedule a viewing appointment?",
        "Show me studio listings in Downtown.",
    ],
)
def test_property_inquiries_do_not_skip_retrieval(query: str) -> None:
    assert should_skip_retrieval(query) is False


@pytest.mark.parametrize(
    "query",
    [
        "Hello, do you have any 3-bed villas in Marina?",
        "Hi, what is the price of studio apartments?",
        "Good morning! Tell me about the payment plan for Lotus.",
        "Salam, how much is the down payment for 1 BHK?",
        "Thanks, what about the handover date?",
    ],
)
def test_mixed_greeting_and_property_inquiry_does_not_skip_retrieval(query: str) -> None:
    # Greetings mixed with real estate terms must ALWAYS trigger retrieval
    assert should_skip_retrieval(query) is False
