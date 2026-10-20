from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import socketio
import structlog
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import dispose_engine
from app.integrations.embeddings.client import close_embedding_client, init_embedding_client
from app.integrations.llm.client import build_llm_client
from app.integrations.qdrant.client import close_qdrant, init_qdrant
from app.integrations.qdrant.collection import ensure_collection
from app.modules.auth.router import router as auth_router
from app.modules.chat.graph_runtime import init_graph, shutdown_graph
from app.modules.chat.redis_pubsub import close_redis_pubsub, init_redis_pubsub  # 12b HITL
from app.modules.chat.router import router as chat_router
from app.modules.chat.socketio_server import sio
from app.modules.knowledge.router import router as knowledge_router
from app.modules.tenants.router import me_router
from app.modules.tenants.router import router as tenants_router
from app.modules.widget.router import router as widget_router
from app.workers.queue import close_queue, init_queue

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log = structlog.get_logger()
    client = init_qdrant()
    init_embedding_client()
    settings = get_settings()
    app.state.llm_client = build_llm_client(settings)
    await init_queue()
    await init_redis_pubsub()  # 12b HITL
    await init_graph()         # 12d HITL LangGraph compiled at startup
    await ensure_collection(client)
    await log.ainfo("app.startup", env=settings.app_env)
    yield
    await shutdown_graph()     # 12d HITL LangGraph
    await close_redis_pubsub()  # 12b HITL
    await close_queue()
    await dispose_engine()
    await close_qdrant()
    await close_embedding_client()
    if hasattr(app.state, "llm_client") and app.state.llm_client is not None:
        await app.state.llm_client.close()
    await log.ainfo("app.shutdown")



def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, json_logs=settings.is_production)

    app = FastAPI(
        title="RealEstate AI",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
    )

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


fastapi_app = create_app()
fastapi_app.include_router(auth_router, prefix="/api/v1")
fastapi_app.include_router(tenants_router, prefix="/api/v1")
fastapi_app.include_router(me_router, prefix="/api/v1")
fastapi_app.include_router(knowledge_router, prefix="/api/v1")
fastapi_app.include_router(chat_router, prefix="/api/v1")
fastapi_app.include_router(widget_router, prefix="/api/v1")
# 12c HITL - Mount Socket.IO as ASGI wrapper so uvicorn app.main:app serves both
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app, socketio_path="socket.io")
