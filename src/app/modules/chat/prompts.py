from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

from app.integrations.llm.base import ChatMessage
from app.modules.knowledge.retrieval import RetrievedChunk

_PROMPT_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
_PROMPT_FILE = _PROMPT_DIR / "real_estate_assistant.md"


@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    if _PROMPT_FILE.exists():
        return _PROMPT_FILE.read_text(encoding="utf-8").strip()
    return (
        "You are an expert, professional, and courteous Real Estate Assistant. "
        "Answer questions based on the provided context."
    )


def format_context_block(chunks: Sequence[RetrievedChunk]) -> str:
    if not chunks:
        return "No specific context documents were found matching this inquiry."

    sections: list[str] = ["### Context Documents:"]
    for i, chunk in enumerate(chunks, start=1):
        page_info = f", Page {chunk.page_number}" if chunk.page_number > 0 else ""
        header = f"[{i}] Source: \"{chunk.document_title}\"{page_info}"
        sections.append(f"{header}\n{chunk.text.strip()}")

    return "\n\n".join(sections)


def build_chat_messages(
    *,
    user_query: str,
    context_chunks: Sequence[RetrievedChunk],
    history: Sequence[ChatMessage] | None = None,
    system_prompt: str | None = None,
) -> list[ChatMessage]:
    base_prompt = system_prompt or load_system_prompt()
    context_block = format_context_block(context_chunks)

    system_content = (
        f"{base_prompt}\n\n"
        f"---\n"
        f"{context_block}\n"
        f"---\n"
        "Instructions: Use the above context documents to answer the client's inquiry accurately. "
        "If the information is not in the context, politely state so."
    )

    messages: list[ChatMessage] = [ChatMessage(role="system", content=system_content)]

    if history:
        for msg in history:
            # Skip any existing system prompts from DB history to avoid confusion
            if msg.role in ("user", "assistant"):
                messages.append(ChatMessage(role=msg.role, content=msg.content))

    messages.append(ChatMessage(role="user", content=user_query))
    return messages


# 12b HITL - AI Conversation Summarizer Prompt for Live Agent Handover
def build_summary_messages(history: Sequence[ChatMessage]) -> list[ChatMessage]:
    """Builds a prompt instructing the LLM to generate a concise JSON handover summary."""
    transcript = []
    for msg in history:
        sender = "Visitor" if msg.role == "user" else "Assistant"
        transcript.append(f"{sender}: {msg.content.strip()}")
    dialogue = "\n".join(transcript)

    system_prompt = (
        "You are an executive real-estate assistant summarizing a visitor conversation for a live human broker.\n"
        "Extract the visitor's core requirement and return ONLY valid JSON with this exact structure:\n"
        "{\n"
        '  "summary": "Concise 1-2 sentence overview of what the client is asking for.",\n'
        '  "key_intent": "Key requirement or property type (e.g., 3-Bedroom Villa, Off-plan Investment)",\n'
        '  "budget": "Stated budget or price range if mentioned, else null",\n'
        '  "preferred_location": "Preferred areas or communities if mentioned, else null"\n'
        "}\n"
        "Do not include any Markdown ticks or extra commentary. Return only the JSON object."
    )

    user_prompt = f"Visitor Transcript:\n{dialogue}\n\nGenerate the summary JSON."
    return [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=user_prompt),
    ]

