import uuid
from unittest.mock import create_autospec

import pytest
from arq.worker import Retry

from app.modules.knowledge.ingestion_runner import IngestionRunner, TransientIngestionError
from app.workers.tasks import INGEST_MAX_TRIES, ingest_document, retry_delay

TENANT_ID = uuid.uuid4()
DOCUMENT_ID = uuid.uuid4()


@pytest.mark.parametrize(
    ("attempt", "expected"),
    [(1, 15), (2, 30), (3, 60), (4, 120), (5, 240), (6, 300), (20, 300)],
)
def test_retry_delay_is_exponential_and_capped(attempt: int, expected: int) -> None:
    assert retry_delay(attempt) == expected


async def test_task_passes_parsed_ids_and_attempt_to_runner() -> None:
    runner: IngestionRunner = create_autospec(IngestionRunner, instance=True)
    ctx = {"ingestion_runner": runner, "job_try": 2}

    await ingest_document(ctx, str(TENANT_ID), str(DOCUMENT_ID))

    runner.run.assert_awaited_once_with(  # type: ignore[attr-defined]
        tenant_id=TENANT_ID,
        document_id=DOCUMENT_ID,
        attempt=2,
        max_attempts=INGEST_MAX_TRIES,
    )


async def test_transient_error_becomes_arq_retry_with_backoff() -> None:
    runner: IngestionRunner = create_autospec(IngestionRunner, instance=True)
    runner.run.side_effect = TransientIngestionError("boom")  # type: ignore[attr-defined]
    ctx = {"ingestion_runner": runner, "job_try": 1}

    with pytest.raises(Retry) as exc_info:
        await ingest_document(ctx, str(TENANT_ID), str(DOCUMENT_ID))

    assert exc_info.value.defer_score == retry_delay(1) * 1000  # arq stores milliseconds


async def test_invalid_uuid_fails_loudly() -> None:
    runner: IngestionRunner = create_autospec(IngestionRunner, instance=True)
    ctx = {"ingestion_runner": runner, "job_try": 1}

    with pytest.raises(ValueError):
        await ingest_document(ctx, "not-a-uuid", str(DOCUMENT_ID))