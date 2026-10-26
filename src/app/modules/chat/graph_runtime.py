# LangGraph runtime: graph lifecycle, retrieval adapter, and turn helpers.
from __future__ import annotations

import logging
from typing import Any
import uuid

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
import redis.asyncio as aioredis

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.integrations.embeddings.client import get_embedding_client
from app.integrations.llm.client import build_llm_client
from app.integrations.qdrant.client import get_qdrant
from app.modules.chat.graph_state import make_turn_input
from app.modules.chat.hitl_graph import (
    ConversationBusyError,
    HitlConfig,
    build_hitl_graph,
    record_human_agent_message,
    run_turn,
)
from app.modules.knowledge.repository import KnowledgeDocumentRepository
from app.modules.knowledge.retrieval import RetrievalService, RetrievedChunk
from app.modules.knowledge.vector_store import ChunkVectorStore

logger = logging.getLogger(__name__)

_graph: CompiledStateGraph | None = None
_pool: Any = None
_llm: Any = None
 

# ==============================================================================
# Retrieval adapter (short-lived DB session per search)
# ==============================================================================


class ScopedRetrievalService:
    def __init__(self, settings: Any) -> None:
        self._settings = settings

    async def search(
        self, *, tenant_id: uuid.UUID, query: str, limit: int | None = None
    ) -> list[RetrievedChunk]:
        async with get_sessionmaker()() as db_session:
            retrieval = RetrievalService(
                embedder=get_embedding_client(),
                store=ChunkVectorStore(get_qdrant(), self._settings.qdrant_collection),
                repository=KnowledgeDocumentRepository(db_session),
                default_limit=limit or self._settings.retrieval_top_k,
                score_threshold=self._settings.retrieval_score_threshold,
            )
            return await retrieval.search(tenant_id=tenant_id, query=query, limit=limit)


# ==============================================================================
# Lifecycle: call init_graph() at startup, shutdown_graph() at shutdown
# ==============================================================================


async def _build_checkpointer(settings: Any) -> BaseCheckpointSaver:
    # Plain postgresql:// DSN (psycopg style), NOT the SQLAlchemy/asyncpg URL.
    dsn = getattr(settings, "langgraph_checkpoint_dsn", None)
    if not dsn:
        logger.warning("[Graph] No langgraph_checkpoint_dsn set, using MemorySaver (DEV ONLY)")
        return MemorySaver()

    global _pool
    pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]] = AsyncConnectionPool(
        conninfo=dsn,
        max_size=20,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=False,
    )
    await pool.open()
    _pool = pool
    saver = AsyncPostgresSaver(pool)
    await saver.setup()
    return saver


async def init_graph() -> None:
    global _graph, _llm
    if _graph is not None:
        return
    settings = get_settings()
    checkpointer = await _build_checkpointer(settings)
    _llm = build_llm_client(settings)
    _graph = build_hitl_graph(
        retrieval_service=ScopedRetrievalService(settings),
        llm=_llm,
        checkpointer=checkpointer,
        cfg=HitlConfig(),
    )
    logger.info("[Graph] HITL LangGraph compiled and cached.")


async def shutdown_graph() -> None:
    global _graph, _pool, _llm
    _graph = None
    if _llm is not None:
        await _llm.close()
        _llm = None
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_graph() -> CompiledStateGraph:
    if _graph is None:
        raise RuntimeError("Graph not initialised. Call init_graph() in app startup.")
    return _graph


def get_redis() -> aioredis.Redis | None:
    try:
        from app.modules.chat import redis_pubsub

        return redis_pubsub._redis_client
    except Exception:
        return None


# ==============================================================================
# Turn helpers used by the socket gateway
# ==============================================================================


async def run_visitor_turn(
    *,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    content: str,
    status: str,
    assigned_agent_id: uuid.UUID | None,
    channel: str = "web",
) -> dict[str, Any] | None:
    """Runs one visitor turn. Returns graph result, or None if it failed / conversation busy."""
    turn_input = {
        **make_turn_input(
            message=HumanMessage(content=content),
            status=status,  # type: ignore[arg-type]
            assigned_agent_id=assigned_agent_id,
        ),
        # Identity is sent every turn so the very first turn of a thread has it too.
        "conversation_id": str(conversation_id),
        "tenant_id": str(tenant_id),
        "channel": channel,
    }
    try:
        return await run_turn(
            get_graph(),
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            turn_input=turn_input,
            redis=get_redis(),
        )
    except ConversationBusyError:
        logger.warning("[Graph] Conversation busy: conv=%s", conversation_id)
    except Exception:
        logger.exception("[Graph] Turn failed: conv=%s", conversation_id)
    return None


async def sync_agent_message(
    *,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    agent_id: uuid.UUID,
    content: str,
) -> None:
    """Resets the 5-minute inactivity clock and adds the agent's words to graph history."""
    try:
        await record_human_agent_message(
            get_graph(),
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            agent_id=agent_id,
            content=content,
            redis=get_redis(),
        )
    except Exception:
        logger.exception("[Graph] Failed to sync agent message: conv=%s", conversation_id)

