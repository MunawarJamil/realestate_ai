import uuid
from unittest.mock import create_autospec

import pytest
from arq.connections import ArqRedis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.modules.knowledge.exceptions import QueueUnavailableError
from app.workers.queue import INGEST_DOCUMENT_JOB, ArqIngestionQueue
from app.workers.tasks import ingest_document

TENANT_ID = uuid.uuid4()
DOCUMENT_ID = uuid.uuid4()


def test_job_name_matches_registered_task() -> None:
    assert INGEST_DOCUMENT_JOB == ingest_document.__name__


async def test_enqueue_sends_string_ids_and_a_deduplicating_job_id() -> None:
    pool: ArqRedis = create_autospec(ArqRedis, instance=True)

    await ArqIngestionQueue(pool).enqueue(tenant_id=TENANT_ID, document_id=DOCUMENT_ID)

    pool.enqueue_job.assert_awaited_once_with(  # type: ignore[attr-defined]
        INGEST_DOCUMENT_JOB, str(TENANT_ID), str(DOCUMENT_ID), _job_id=f"ingest:{DOCUMENT_ID}"
    )


@pytest.mark.parametrize("error", [RedisConnectionError("down"), OSError("network unreachable")])
async def test_redis_failures_become_queue_unavailable(error: Exception) -> None:
    pool: ArqRedis = create_autospec(ArqRedis, instance=True)
    pool.enqueue_job.side_effect = error  # type: ignore[attr-defined]

    with pytest.raises(QueueUnavailableError):
        await ArqIngestionQueue(pool).enqueue(tenant_id=TENANT_ID, document_id=DOCUMENT_ID)