import asyncio
from typing import Any

from arq.connections import RedisSettings
from arq.worker import func

# Python 3.12+ no longer creates an implicit event loop on asyncio.get_event_loop().
# arq 0.25 relies on asyncio.get_event_loop() in Worker.__init__, so ensure one is set.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())


from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import dispose_engine, get_sessionmaker
from app.integrations.embeddings.client import close_embedding_client, init_embedding_client
from app.integrations.qdrant.client import close_qdrant, get_qdrant, init_qdrant
from app.modules.knowledge.ingestion import build_ingestion_pipeline
from app.modules.knowledge.ingestion_runner import IngestionRunner
from app.modules.knowledge.repository import repository_scope
from app.modules.knowledge.storage import build_file_storage
from app.modules.knowledge.vector_store import ChunkVectorStore
from app.workers.tasks import INGEST_MAX_TRIES, INGEST_TIMEOUT_SECONDS, ingest_document


async def on_startup(ctx: dict[str, Any]) -> None:
    # Call the same logging setup that main.py's lifespan uses (from core/logging.py) here.
    settings = get_settings()
    configure_logging(settings.log_level, json_logs=settings.is_production)    
    init_qdrant()
    init_embedding_client()
    ctx["ingestion_runner"] = IngestionRunner(
        repository_scope=repository_scope(get_sessionmaker()),
        storage=build_file_storage(),
        pipeline=build_ingestion_pipeline(),
        store=ChunkVectorStore(get_qdrant(), settings.qdrant_collection),
    )


async def on_shutdown(ctx: dict[str, Any]) -> None:
    await close_embedding_client()
    await close_qdrant()
    await dispose_engine()


class WorkerSettings:
    functions = [func(ingest_document, max_tries=INGEST_MAX_TRIES, timeout=INGEST_TIMEOUT_SECONDS)]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    on_startup = on_startup
    on_shutdown = on_shutdown
    max_jobs = 4
    keep_result = 3600
    health_check_interval = 30