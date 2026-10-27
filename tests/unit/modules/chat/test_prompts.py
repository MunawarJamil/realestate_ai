import uuid

from app.integrations.llm.base import ChatMessage
from app.modules.chat.prompts import (
    build_chat_messages,
    format_context_block,
    load_system_prompt,
)
from app.modules.knowledge.retrieval import RetrievedChunk


def test_load_system_prompt_returns_content() -> None:
    prompt = load_system_prompt()
    assert "Real Estate Assistant" in prompt
    assert "Factual Grounding" in prompt or "Grounding" in prompt


def test_format_context_block_empty() -> None:
    block = format_context_block([])
    assert "No specific reference documents attached" in block


def test_format_context_block_with_chunks() -> None:
    chunks = [
        RetrievedChunk(
            document_id=uuid.uuid4(),
            document_title="Marina Heights Brochure.pdf",
            page_number=3,
            chunk_index=0,
            text="2-bedroom units start at $450,000 with balcony views.",
            score=0.88,
        ),
        RetrievedChunk(
            document_id=uuid.uuid4(),
            document_title="Floorplans.pdf",
            page_number=0,
            chunk_index=1,
            text="Swimming pool and fitness center on 5th floor.",
            score=0.75,
        ),
    ]

    block = format_context_block(chunks)
    assert 'Source: "Marina Heights Brochure.pdf", Page 3' in block
    assert "2-bedroom units start at $450,000" in block
    assert 'Source: "Floorplans.pdf"' in block
    assert "Swimming pool and fitness center" in block


def test_build_chat_messages_structure() -> None:
    chunks = [
        RetrievedChunk(
            document_id=uuid.uuid4(),
            document_title="Pricing.pdf",
            page_number=1,
            chunk_index=0,
            text="Down payment is 10%.",
            score=0.9,
        )
    ]
    history = [
        ChatMessage(role="system", content="Old system prompt to skip"),
        ChatMessage(role="user", content="Hello, tell me about Marina Heights."),
        ChatMessage(role="assistant", content="Marina Heights is a luxury waterfront development."),
    ]

    messages = build_chat_messages(
        user_query="What is the down payment?",
        context_chunks=chunks,
        history=history,
    )

    # First message: System prompt + context documents
    assert len(messages) == 4
    assert messages[0].role == "system"
    assert "Down payment is 10%." in messages[0].content
    assert "Real Estate Assistant" in messages[0].content

    # Second & Third: History turns (system message was skipped)
    assert messages[1].role == "user"
    assert messages[1].content == "Hello, tell me about Marina Heights."
    assert messages[2].role == "assistant"
    assert messages[2].content == "Marina Heights is a luxury waterfront development."

    # Fourth: Current user inquiry
    assert messages[3].role == "user"
    assert messages[3].content == "What is the down payment?"


def test_build_query_condensation_messages() -> None:
    from app.modules.chat.prompts import build_query_condensation_messages

    history = [
        ChatMessage(role="user", content="Tell me about Lotus at Creek Beach."),
        ChatMessage(role="assistant", content="Lotus at Creek Beach offers luxury apartments."),
    ]

    messages = build_query_condensation_messages(
        user_query="How much for the 2-bed one?",
        history=history,
    )

    assert len(messages) == 2
    assert messages[0].role == "system"
    assert "rephrase the follow-up into a single, standalone search query" in messages[0].content
    assert messages[1].role == "user"
    assert "Visitor: Tell me about Lotus at Creek Beach." in messages[1].content
    assert "Assistant: Lotus at Creek Beach offers luxury apartments." in messages[1].content

    assert "Follow-up Inquiry: How much for the 2-bed one?" in messages[1].content

