import logging
import uuid
from typing import Final

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.modules.knowledge.exceptions import QueueUnavailableError

logger = logging.getLogger(__name__)

INGEST_DOCUMENT_JOB: Final = "ingest_document"  # must equal the registered task name

_pool: ArqRedis | None = None


class ArqIngestionQueue:
    def __init__(self, pool: ArqRedis) -> None:
        self._pool = pool

    async def enqueue(self, *, tenant_id: uuid.UUID, document_id: uuid.UUID) -> None:
        try:
            # Fixed job id: enqueueing the same document twice never creates a second job.
            await self._pool.enqueue_job(
                INGEST_DOCUMENT_JOB,
                str(tenant_id),
                str(document_id),
                _job_id=f"ingest:{document_id}",
            )
        except (RedisError, OSError) as exc:
            logger.error("Could not enqueue ingestion for document %s: %r", document_id, exc)
            raise QueueUnavailableError("Job queue is unavailable.") from exc


async def init_queue() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    return _pool


def get_ingestion_queue() -> ArqIngestionQueue:
    if _pool is None:
        raise RuntimeError("Queue is not initialised. Call init_queue() at startup.")
    return ArqIngestionQueue(_pool)


async def close_queue() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None