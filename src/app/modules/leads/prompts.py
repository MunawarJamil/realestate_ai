from __future__ import annotations

from typing import Sequence
from app.integrations.llm.base import ChatMessage

LEAD_EXTRACTION_SYSTEM_PROMPT = """You are an expert Real Estate CRM Lead Qualification Analyst.
Your task is to analyze the conversation between a prospective client (visitor) and the real estate AI assistant / broker.

Extract structured lead qualification data with maximum precision and zero hallucination.
If a specific field was NOT mentioned by the visitor, set it to null. Do NOT fabricate details.

Evaluate lead quality strictly against the 100-point Auto-Qualification Matrix:
1. Budget Score (0 to 30 pts):
   - 30 pts: Explicit numerical min and max budget stated.
   - 20 pts: Single explicit target or max budget stated.
   - 10 pts: Vague budget range (e.g. "affordable", "luxury").
   - 0 pts: No budget mentioned.

2. Timeline Score (0 to 25 pts):
   - 25 pts: Immediate purchase / move-in within 30 days.
   - 15 pts: 1 to 3 months.
   - 5 pts: 3 to 6 months or "just looking for next year".
   - 0 pts: No timeline mentioned.

3. Intent Score (0 to 25 pts):
   - 25 pts: Direct buyer or serious investor asking for viewing, payment plan, or contract.
   - 15 pts: Rental inquiry or general property interest.
   - 5 pts: Curious visitor asking broad questions.
   - 0 pts: Off-topic or non-real-estate conversation.

4. Contact Score (0 to 20 pts):
   - 20 pts: Both phone number and email provided.
   - 15 pts: Valid phone number provided.
   - 10 pts: Valid email provided.
   - 0 pts: No contact details provided.

Return ONLY a valid JSON object matching this schema without any markdown commentary:
{
  "has_lead_indicators": boolean,
  "contact_name": string | null,
  "email": string | null,
  "phone": string | null,
  "intent": "buy" | "rent" | "invest" | "sell",
  "property_type": string | null,
  "preferred_location": string | null,
  "timeline": string | null,
  "budget_min": number | null,
  "budget_max": number | null,
  "currency": string,
  "notes": string | null,
  "budget_score": number,
  "timeline_score": number,
  "intent_score": number,
  "contact_score": number,
  "rationale": string
}
"""


def build_lead_extraction_messages(history: Sequence[ChatMessage]) -> list[ChatMessage]:
    transcript_lines = []
    for msg in history:
        sender = "Visitor" if msg.role == "user" else "Assistant"
        transcript_lines.append(f"{sender}: {msg.content}")

    conversation_text = "\n".join(transcript_lines)

    user_prompt = f"""Here is the chat conversation transcript to analyze:

--- BEGIN TRANSCRIPT ---
{conversation_text}
--- END TRANSCRIPT ---

Analyze the transcript and produce the JSON lead extraction according to the Auto-Qualification Matrix."""

    return [
        ChatMessage(role="system", content=LEAD_EXTRACTION_SYSTEM_PROMPT),
        ChatMessage(role="user", content=user_prompt),
    ]
