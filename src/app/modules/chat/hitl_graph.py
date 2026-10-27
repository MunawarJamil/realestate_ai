# 12d HITL - Production-Grade LangGraph Orchestrator for RealEstate AI
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import logging
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast
import uuid

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from redis.exceptions import LockError

from app.integrations.llm.base import ChatMessage, LLMProvider
from app.modules.chat.graph_state import AgentState, utc_now_iso
from app.modules.chat.handoff import HANDOFF_GUARDRAIL_REPLY, detect_handoff_request
from app.modules.chat.prompts import build_chat_messages
from app.modules.knowledge.retrieval import RetrievedChunk


if TYPE_CHECKING:
    from redis.asyncio import Redis


# 12e improvements

import re

# High-frequency multilingual greetings, small-talk, acknowledgments & bot identity inquiries
_SMALLTALK_EXACT = {
    # English greetings & pleasantries
    "hello", "hi", "hey", "hiya", "howdy", "good morning", "good afternoon",
    "good evening", "greetings", "welcome", "thanks", "thank you", "thx", "ty",
    "bye", "goodbye", "cya", "see you", "have a good day",
    # Arabic greetings & pleasantries
    "salam", "assalam alaikum", "marhaba", "ahlan", "hala", "shukran", "ahlan wa sahlan",
    # Roman Urdu / Hindi
    "kya hal hai", "kaise ho", "shukriya", "adaab",
    # Common conversational fillers / acknowledgments
    "ok", "okay", "sure", "got it", "understood", "waiting", "i am waiting",
    "yes", "no", "cool", "great", "nice", "fine",
    # Bot capability / identity
    "who are you", "what are you", "what can you do", "help", "are you ai",
    "are you a bot", "are you a human", "can you help me", "how does this work",
}

_SMALLTALK_PATTERNS = [
    re.compile(r"^(hi|hello|hey|salam|marhaba|hola)\b", re.IGNORECASE),
    re.compile(r"\b(how are you|how's it going|who are you|what can you do)\b", re.IGNORECASE),
    re.compile(r"^(thank you|thanks|good morning|good evening|good afternoon)\b", re.IGNORECASE),
    re.compile(r"^(ok|okay|waiting|still waiting)\b", re.IGNORECASE),
]

_REAL_ESTATE_SIGNALS = [
    re.compile(
        r"\b(villa|apartment|flat|penthouse|studio|duplex|land|plot|commercial|office|building)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(buy|rent|sale|purchase|invest|lease|price|cost|budget|jod|usd|aed|dollar|sqm|sqft|bedroom|bhk|bath)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(amman|aqaba|dabouq|abdoun|deir ghbar|swifieh|khalda|jubeiha|viewing|tour|listing|catalog)\b",
        re.IGNORECASE,
    ),
]


def classify_visitor_intent(text: str) -> Literal["smalltalk", "property_inquiry"]:
    """
    Production-grade, zero-latency intent classifier.
    
    1. If message strongly contains real-estate domain signals -> property_inquiry.
    2. If message matches greeting, filler, or bot-identity patterns -> smalltalk.
    3. If uncertain -> defaults to property_inquiry (RAG flow with full safety).
    """
    clean = re.sub(r"[^\w\s]", " ", text).strip().lower()
    single_spaced = " ".join(clean.split())

    if not single_spaced:
        return "smalltalk"

    # 1. Check for explicit property signals first
    for pattern in _REAL_ESTATE_SIGNALS:
        if pattern.search(single_spaced):
            return "property_inquiry"

    # 2. Check exact smalltalk dictionary
    if single_spaced in _SMALLTALK_EXACT:
        return "smalltalk"

    # 3. Check regex pattern prefixes
    for pattern in _SMALLTALK_PATTERNS:
        if pattern.search(single_spaced):
            return "smalltalk"

    # 4. Short casual messages (<= 3 words) without property signals
    words = single_spaced.split()
    if len(words) <= 2 and words[0] in {"hi", "hello", "hey", "salam", "thanks", "ok", "waiting"}:
        return "smalltalk"

    # 5. Default fallback: keep normal RAG flow
    return "property_inquiry"

# 12e improvements ended


logger = logging.getLogger(__name__)

HUMAN_AGENT_NAME = "human_agent"

LLM_FALLBACK_REPLY = (
    "Sorry, I'm having a little trouble right now. Please try again in a moment."
)
NO_CONTEXT_REPLY = (
    "I'm sorry, I couldn't quite understand your message. Could you please rephrase your question so I can help you?"
)


# Config (all tunables in one place, injectable for tests)


@dataclass(frozen=True, slots=True)
class HitlConfig:
    human_inactivity_timeout: float = 300.0   # 5 min: agent silent -> AI takes back
    unclaimed_handoff_timeout: float = 600.0  # 10 min: nobody accepted handoff -> AI takes back
    max_ai_failures: int = 3                  # consecutive failures -> handoff to human
    max_history_messages: int = 20            # messages sent to LLM (state keeps everything)
    retrieval_timeout: float = 10.0
    llm_timeout: float = 30.0
    llm_retries: int = 1
    require_grounding: bool = True            # no knowledge chunks -> don't let LLM guess
    lock_ttl: int = 60                        # seconds, per-conversation Redis lock
    lock_wait: int = 15


DEFAULT_CONFIG = HitlConfig()


# ==============================================================================
# Dependencies (Protocols so clients are injected, not rebuilt per turn)
# ==============================================================================


class SearchService(Protocol):
    """Protocol satisfied by both RetrievalService and ScopedRetrievalService."""

    async def search(
        self, *, tenant_id: uuid.UUID, query: str, limit: int | None = None
    ) -> list[RetrievedChunk]: ...


class ConversationBusyError(RuntimeError):
    """Another turn is already running for this conversation."""



def _utcnow() -> datetime:
    return datetime.now(UTC)


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _last_human_index(messages: list[BaseMessage]) -> int | None:
    for idx in range(len(messages) - 1, -1, -1):
        if isinstance(messages[idx], HumanMessage):
            return idx
    return None


def _log_ctx(state: AgentState) -> dict[str, Any]:
    return {
        "conversation_id": state.get("conversation_id"),
        "tenant_id": state.get("tenant_id"),
    }


def _to_llm_history(messages: list[BaseMessage], upto: int, limit: int) -> list[ChatMessage]:
    """Messages before the current query, trimmed to the last `limit`.
    Human-agent messages are AIMessage too, so the AI sees what the agent said."""
    prior = messages[:upto][-limit:] if limit > 0 else []
    return [
        ChatMessage(
            role="user" if isinstance(m, HumanMessage) else "assistant",
            content=str(m.content),
        )
        for m in prior
    ]


async def _call_with_retry[T](
    factory: Callable[[], Awaitable[T]],
    *,
    timeout: float,
    retries: int,
    backoff: float = 0.5,
) -> T:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await asyncio.wait_for(factory(), timeout=timeout)
        except Exception as exc:  # CancelledError is BaseException, so it propagates
            last_exc = exc
            if attempt < retries:
                await asyncio.sleep(backoff * (2**attempt))
    assert last_exc is not None
    raise last_exc


def _ai_reclaim_updates() -> dict[str, Any]:
    """State changes when the AI takes the conversation back."""
    return {
        "status": "ai",
        "assigned_agent_id": None,
        "handoff_reason": None,
        "handoff_requested_at": None,
        "last_human_activity_at": None,
        "handoff_notice_sent": False,
        "ai_failure_count": 0,
    }


def _handoff_updates(reason: str) -> dict[str, Any]:
    return {
        "requires_human": True,
        "status": "handoff_requested",
        "handoff_reason": reason,
        "handoff_requested_at": utc_now_iso(),
        "last_human_activity_at": None,
        "handoff_notice_sent": False,
    }

# Node 1: Intent & Lifecycle Router (includes the 5-minute inactivity check)


def make_intent_router_node(cfg: HitlConfig = DEFAULT_CONFIG):
    async def intent_router_node(state: AgentState) -> dict[str, Any]:
        status = state.get("status", "ai")
        now = _utcnow()
        updates: dict[str, Any] = {}

        if status == "resolved":
            logger.info("Reopening resolved conversation", extra=_log_ctx(state))
            updates = _ai_reclaim_updates()
            status = "ai"

        elif status == "human_active":
            last_activity = _parse_ts(state.get("last_human_activity_at")) or _parse_ts(
                state.get("handoff_requested_at")
            )
            if last_activity is None:
                return {
                    "requires_human": True,
                    "intent": "live_human_support",
                    "last_human_activity_at": now.isoformat(),
                }
            idle = (now - last_activity).total_seconds()
            if idle >= cfg.human_inactivity_timeout:
                logger.info("Human agent idle %.0fs, AI reclaiming conversation", idle, extra=_log_ctx(state))
                updates = _ai_reclaim_updates()
                status = "ai"
            else:
                return {"requires_human": True, "intent": "live_human_support"}

        elif status == "handoff_requested":
            requested_at = _parse_ts(state.get("handoff_requested_at"))
            waited = (now - requested_at).total_seconds() if requested_at else 0.0
            if requested_at and waited >= cfg.unclaimed_handoff_timeout:
                logger.info("Handoff unclaimed for %.0fs, AI reclaiming conversation", waited, extra=_log_ctx(state))
                updates = _ai_reclaim_updates()
                status = "ai"
            else:
                return {"requires_human": True, "intent": "live_human_support"}

        # status == "ai" (originally, or just reclaimed)
        messages = state.get("messages", [])
        idx = _last_human_index(messages)
        last_text = str(messages[idx].content) if idx is not None else ""

        # Check for handoff request
        if detect_handoff_request(last_text, state.get("metadata", {})):
            return {
                **updates,
                **_handoff_updates("user_request"),
                "intent": "handoff_requested",
            }

        # Classify between smalltalk and property_inquiry
        intent = classify_visitor_intent(last_text)
        return {
            **updates,
            "requires_human": False,
            "intent": intent,
        }

    return intent_router_node


SMALLTALK_SYSTEM_PROMPT = """You are a helpful, courteous, and professional AI Assistant for a premier real estate agency.
Your role in this turn is to greet the visitor, acknowledge their comment, or clarify your role.
- Be polite, warm, concise, and professional (max 2-3 sentences).
- If the visitor is greeting you, welcome them and invite them to ask about available properties, locations, or pricing.
- If the visitor is waiting for an advisor, reassure them politely and offer to answer any preliminary questions while they wait.
- CRITICAL: Do NOT invent, assume, or list specific property names, addresses, or prices in small-talk mode."""


def make_smalltalk_node(llm: LLMProvider, cfg: HitlConfig = DEFAULT_CONFIG):
    async def smalltalk_node(state: AgentState) -> dict[str, Any]:
        ctx = _log_ctx(state)
        messages = state.get("messages", [])
        idx = _last_human_index(messages)
        query = str(messages[idx].content) if idx is not None else "Hello"

        history_msgs = _to_llm_history(messages, idx, limit=4) if idx is not None else []
        prompt_messages = [
            ChatMessage(role="system", content=SMALLTALK_SYSTEM_PROMPT),
            *history_msgs,
            ChatMessage(role="user", content=query),
        ]

        try:
            # Low max_tokens to preserve speed and avoid cost
            resp = await _call_with_retry(
                lambda: llm.complete(prompt_messages, max_tokens=150, temperature=0.6),
                timeout=cfg.llm_timeout,
                retries=1,
            )
            reply = (resp.content or "").strip()
            if not reply:
                reply = "Hello! Welcome to our agency. How can I assist you with properties or pricing today?"
        except Exception:
            logger.exception("Small-talk generation failed, using fallback", extra=ctx)
            reply = "Hello! Welcome to our agency. How can I assist you with your property search today?"

        return {
            "context_chunks": [],
            "retrieval_failed": False,
            "ai_failure_count": 0,
            "reply_content": reply,
            "messages": [AIMessage(content=reply)],
        }

    return smalltalk_node




# Node 2: Human Review (HITL silence / one-time notice)

async def human_review_node(state: AgentState) -> dict[str, Any]:
    """Human agent active -> AI silent. Handoff notice is sent only ONCE."""
    if state.get("status") == "human_active" or state.get("handoff_notice_sent"):
        return {"reply_content": None}

    return {
        "reply_content": HANDOFF_GUARDRAIL_REPLY,
        "messages": [AIMessage(content=HANDOFF_GUARDRAIL_REPLY)],
        "handoff_notice_sent": True,
    }


# ==============================================================================
# Node 3: Grounded RAG + LLM generation
# ==============================================================================


def _failure_result(
    state: AgentState, cfg: HitlConfig, *, retrieval_failed: bool
) -> dict[str, Any]:
    """Counts a failed AI turn. After N consecutive failures, escalate to a human."""
    count = int(state.get("ai_failure_count", 0)) + 1
    base: dict[str, Any] = {
        "ai_failure_count": count,
        "retrieval_failed": retrieval_failed,
        "context_chunks": [],
    }
    if count >= cfg.max_ai_failures:
        logger.error(
            "AI failed %d times in a row, escalating to human", count, extra=_log_ctx(state)
        )
        return {
            **base,
            **_handoff_updates("ai_failure"),
            "handoff_notice_sent": True,
            "reply_content": HANDOFF_GUARDRAIL_REPLY,
            "messages": [AIMessage(content=HANDOFF_GUARDRAIL_REPLY)],
        }
    # Visitor still gets a reply, but it is NOT stored as a real AI message in history.
    return {**base, "reply_content": LLM_FALLBACK_REPLY}


def make_rag_node(
    llm: LLMProvider,
    retrieval_service: SearchService | None = None,
    cfg: HitlConfig = DEFAULT_CONFIG,
):
    async def rag_node(state: AgentState) -> dict[str, Any]:
        ctx = _log_ctx(state)
        messages = state.get("messages", [])
        idx = _last_human_index(messages)
        if idx is None or not str(messages[idx].content).strip():
            return {"reply_content": None}
        query = str(messages[idx].content)
        tenant_id = uuid.UUID(state["tenant_id"])

        # 1. Retrieval (timeout, failure counts toward escalation)
        chunks: list[Any] = []
        if retrieval_service is not None:
            try:
                chunks = await _call_with_retry(
                    lambda: retrieval_service.search(tenant_id=tenant_id, query=query),
                    timeout=cfg.retrieval_timeout,
                    retries=0,
                )
            except Exception:
                logger.exception("Knowledge search failed", extra=ctx)
                return _failure_result(state, cfg, retrieval_failed=True)

        # 2. Hallucination guard: nothing verified -> don't let the LLM guess listings/prices
        if cfg.require_grounding and retrieval_service is not None and not chunks:
            return {
                "reply_content": NO_CONTEXT_REPLY,
                "messages": [AIMessage(content=NO_CONTEXT_REPLY)],
            }

        # 3. LLM call (timeout + limited retry)
        prompt_messages = build_chat_messages(
            user_query=query,
            context_chunks=chunks,
            history=_to_llm_history(messages, idx, cfg.max_history_messages),
        )
        try:
            resp = await _call_with_retry(
                lambda: llm.complete(prompt_messages),
                timeout=cfg.llm_timeout,
                retries=cfg.llm_retries,
            )
            ai_content = (resp.content or "").strip()
            if not ai_content:
                raise ValueError("Empty LLM response")
        except Exception:
            logger.exception("LLM generation failed", extra=ctx)
            return _failure_result(state, cfg, retrieval_failed=False)

        return {
            "context_chunks": [c.text for c in chunks],
            "retrieval_failed": False,
            "ai_failure_count": 0,  # success resets the consecutive-failure counter
            "reply_content": ai_content,
            "messages": [AIMessage(content=ai_content)],
        }

    return rag_node



# Conditional edge

def route_next_step(state: AgentState) -> Literal["human_review", "smalltalk_agent", "rag_agent"]:
    if state.get("requires_human", False):
        return "human_review"
    if state.get("intent") == "smalltalk":
        return "smalltalk_agent"
    return "rag_agent"


# Graph builder: call ONCE at app startup, reuse for all requests


def build_hitl_graph(
    retrieval_service: SearchService | None,
    llm: LLMProvider,
    checkpointer: BaseCheckpointSaver | None = None,
    cfg: HitlConfig = DEFAULT_CONFIG,
) -> CompiledStateGraph:
    if checkpointer is None:
        logger.warning("No checkpointer given, using in-memory MemorySaver (DEV ONLY)")
        checkpointer = MemorySaver()
    workflow = make_hitl_workflow(retrieval_service=retrieval_service, llm=llm, cfg=cfg)
    return workflow.compile(checkpointer=checkpointer)


def make_hitl_workflow(
    retrieval_service: SearchService | None = None,
    llm: LLMProvider | None = None,
    cfg: HitlConfig = DEFAULT_CONFIG,
) -> StateGraph:
    """Constructs the uncompiled StateGraph (used by LangGraph Studio and production)."""
    if llm is None:
        from app.core.config import get_settings
        from app.integrations.llm.client import build_llm_client
        llm = build_llm_client(get_settings())

    workflow: StateGraph = StateGraph(cast(Any, AgentState))
    workflow.add_node("intent_router", make_intent_router_node(cfg))
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("smalltalk_agent", make_smalltalk_node(llm, cfg))
    workflow.add_node("rag_agent", make_rag_node(llm, retrieval_service, cfg))

    workflow.add_edge(START, "intent_router")
    workflow.add_conditional_edges(
        "intent_router",
        route_next_step,
        {
            "human_review": "human_review",
            "smalltalk_agent": "smalltalk_agent",
            "rag_agent": "rag_agent",
        },
    )
    workflow.add_edge("human_review", END)
    workflow.add_edge("smalltalk_agent", END)
    workflow.add_edge("rag_agent", END)
    return workflow

# Runtime helpers: thread config, per-conversation lock, running a turn


def build_thread_config(
    tenant_id: str | uuid.UUID,
    conversation_id: str | uuid.UUID,
    *,
    assigned_agent_id: str | uuid.UUID | None = None,
    tags: list[str] | None = None,
) -> RunnableConfig:
    """Tenant-scoped thread id & LangSmith trace metadata."""
    metadata = {
        "tenant_id": str(tenant_id),
        "conversation_id": str(conversation_id),
    }
    if assigned_agent_id:
        metadata["assigned_agent_id"] = str(assigned_agent_id)

    return cast(
        RunnableConfig,
        {
            "configurable": {
                "thread_id": f"{tenant_id}:{conversation_id}",
            },
            # 👇 LangSmith tracing attributes
            "metadata": metadata,
            "tags": tags or ["visitor_turn", f"tenant:{tenant_id}"],
        },
    )

@asynccontextmanager
async def conversation_lock(
    redis: Redis | None,
    tenant_id: str | uuid.UUID,
    conversation_id: str | uuid.UUID,
    cfg: HitlConfig = DEFAULT_CONFIG,
) -> AsyncIterator[None]:
    """Only one graph run / state update per conversation at a time."""
    if redis is None:
        yield
        return
    lock = redis.lock(
        f"lock:conv:{tenant_id}:{conversation_id}",
        timeout=cfg.lock_ttl,
        blocking_timeout=cfg.lock_wait,
    )
    if not await lock.acquire():
        raise ConversationBusyError(f"Conversation {conversation_id} is busy")
    try:
        yield
    finally:
        try:
            await lock.release()
        except LockError:
            logger.warning("Conversation lock expired before release: %s", conversation_id)


async def run_turn(
    graph: CompiledStateGraph,
    *,
    tenant_id: str | uuid.UUID,
    conversation_id: str | uuid.UUID,
    turn_input: dict[str, Any],
    redis: Redis | None = None,
    cfg: HitlConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Run one visitor turn. `turn_input` = make_initial_state(...) or make_turn_input(...)."""
    async with conversation_lock(redis, tenant_id, conversation_id, cfg):
        config = build_thread_config(
            tenant_id,
            conversation_id,
            assigned_agent_id=turn_input.get("assigned_agent_id"),
         )
        result = await graph.ainvoke(turn_input, config=config)
        return cast(dict[str, Any], result)


async def record_human_agent_message(
    graph: CompiledStateGraph,
    *,
    tenant_id: str | uuid.UUID,
    conversation_id: str | uuid.UUID,
    agent_id: str | uuid.UUID,
    content: str,
    redis: Redis | None = None,
    cfg: HitlConfig = DEFAULT_CONFIG,
) -> None:
    """Call this whenever a human agent sends a message.
    It (1) restarts the 5-minute inactivity clock, (2) marks the conversation
    human_active, (3) puts the agent's words in graph history so the AI knows
    the context if it takes over later."""
    async with conversation_lock(redis, tenant_id, conversation_id, cfg):
        config = build_thread_config(
            tenant_id,
            conversation_id,
            assigned_agent_id=agent_id,
            tags=["agent_turn", f"tenant:{tenant_id}"],
        )
        await graph.aupdate_state(
            config,
            {
                "messages": [
                    AIMessage(
                        content=content,
                        name=HUMAN_AGENT_NAME,
                        additional_kwargs={"sender_type": "agent", "agent_id": str(agent_id)},
                    )
                ],
                "status": "human_active",
                "assigned_agent_id": str(agent_id),
                "last_human_activity_at": utc_now_iso(),
                "handoff_notice_sent": True,
            },
            as_node="human_review",
        )


# Studio entrypoint instance
builder = make_hitl_workflow()