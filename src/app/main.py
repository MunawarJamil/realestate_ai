from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import dispose_engine
from app.integrations.embeddings.client import close_embedding_client, init_embedding_client
from app.integrations.qdrant.client import close_qdrant, init_qdrant
from app.integrations.qdrant.collection import ensure_collection
from app.modules.tenants.router import me_router
from app.modules.tenants.router import router as tenants_router
from app.modules.knowledge.router import router as knowledge_router
from app.workers.queue import close_queue, init_queue

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log = structlog.get_logger()
    client = init_qdrant()
    init_embedding_client()
    await init_queue()
    await ensure_collection(client)
    await log.ainfo("app.startup", env=get_settings().app_env)
    yield
    await close_queue()
    await dispose_engine()
    await close_qdrant()
    await close_embedding_client()
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

    return app


app = create_app()

app.include_router(tenants_router, prefix="/api/v1")
app.include_router(me_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")