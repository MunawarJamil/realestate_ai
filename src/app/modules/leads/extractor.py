from __future__ import annotations

import json
import logging
import re
import uuid
from decimal import Decimal
from typing import Any

from app.integrations.llm.base import ChatMessage, LLMProvider
from app.modules.chat.models import Message
from app.modules.leads.enums import LeadIntent, LeadStatus
from app.modules.leads.prompts import build_lead_extraction_messages
from app.modules.leads.schemas import LeadRead
from app.modules.leads.service import LeadService

logger = logging.getLogger(__name__)

PHONE_REGEX = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


class LeadExtractionEngine:
    """Extracts structured lead profiles and auto-qualifies them from chat turns."""

    def __init__(self, *, llm: LLMProvider, lead_service: LeadService) -> None:
        self._llm = llm
        self._lead_service = lead_service

    async def extract_and_qualify(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        messages: list[Message],
    ) -> LeadRead | None:
        dialogue = [
            m for m in messages
            if m.role.value in ("user", "assistant") and m.content and m.content.strip()
        ]
        if not dialogue:
            return None

        # Build prompt
        chat_history = [
            ChatMessage(role=m.role.value, content=m.content)
            for m in dialogue
        ]
        prompt = build_lead_extraction_messages(chat_history)

        try:
            llm_response = await self._llm.complete(prompt)
            raw_text = llm_response.content.strip()

            # Clean markdown codeblocks
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()

            data: dict[str, Any] = json.loads(raw_text)
        except Exception as exc:
            logger.warning(
                "Lead extraction failed for conversation_id=%s tenant_id=%s: %r",
                conversation_id,
                tenant_id,
                exc,
            )
            return None

        if not data.get("has_lead_indicators", False):
            logger.debug("No lead indicators found for conversation_id=%s", conversation_id)
            return None

        # Fallback / heuristic regex extraction for contact info if LLM missed it
        all_user_text = " ".join([m.content for m in dialogue if m.role.value == "user"])
        phone = data.get("phone")
        if not phone:
            phone_match = PHONE_REGEX.search(all_user_text)
            if phone_match:
                phone = phone_match.group(0).strip()

        email = data.get("email")
        if not email:
            email_match = EMAIL_REGEX.search(all_user_text)
            if email_match:
                email = email_match.group(0).strip()

        # Score calculation & bounds
        b_score = max(0, min(30, int(data.get("budget_score", 0))))
        t_score = max(0, min(25, int(data.get("timeline_score", 0))))
        i_score = max(0, min(25, int(data.get("intent_score", 0))))

        # Heuristic contact score booster
        c_score = max(0, min(20, int(data.get("contact_score", 0))))
        if phone and email:
            c_score = max(c_score, 20)
        elif phone:
            c_score = max(c_score, 15)
        elif email:
            c_score = max(c_score, 10)

        total_score = min(100, b_score + t_score + i_score + c_score)

        score_breakdown = {
            "budget_score": b_score,
            "timeline_score": t_score,
            "intent_score": i_score,
            "contact_score": c_score,
            "rationale": data.get("rationale", ""),
        }

        # Resolve intent enum safely
        raw_intent = str(data.get("intent", "buy")).lower()
        valid_intents = {m.value: m for m in LeadIntent}
        intent_enum = valid_intents.get(raw_intent, LeadIntent.BUY)

        lead_payload: dict[str, Any] = {
            "contact_name": data.get("contact_name"),
            "email": email,
            "phone": phone,
            "intent": intent_enum,
            "property_type": data.get("property_type"),
            "preferred_location": data.get("preferred_location"),
            "timeline": data.get("timeline"),
            "budget_min": Decimal(str(data["budget_min"])) if data.get("budget_min") is not None else None,
            "budget_max": Decimal(str(data["budget_max"])) if data.get("budget_max") is not None else None,
            "currency": data.get("currency") or "AED",
            "notes": data.get("notes"),
            "ai_score": total_score,
            "score_breakdown": score_breakdown,
            "status": LeadStatus.NEW,
        }

        lead = await self._lead_service.upsert_from_conversation(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            lead_data=lead_payload,
        )

        logger.info(
            "Auto-qualification complete: lead_id=%s tenant_id=%s score=%d category=%s",
            lead.id,
            tenant_id,
            lead.ai_score,
            lead.score_category.value,
        )
        return lead
