import uuid
from typing import Any, Final

from arq.worker import Retry

from app.modules.knowledge.ingestion_runner import IngestionRunner, TransientIngestionError

INGEST_MAX_TRIES: Final = 3
INGEST_TIMEOUT_SECONDS: Final = 900
_RETRY_BASE_SECONDS: Final = 15
_RETRY_MAX_SECONDS: Final = 300


def retry_delay(attempt: int) -> int:
    """Exponential backoff in seconds: 15, 30, 60 ... capped at 5 minutes."""
    return min(_RETRY_BASE_SECONDS * 2 ** (attempt - 1), _RETRY_MAX_SECONDS)


async def ingest_document(ctx: dict[str, Any], tenant_id: str, document_id: str) -> None:
    """ARQ job. Arguments are plain strings so they serialize safely through Redis."""
    runner: IngestionRunner = ctx["ingestion_runner"]
    attempt: int = ctx["job_try"]  # 1-based
    try:
        await runner.run(
            tenant_id=uuid.UUID(tenant_id),
            document_id=uuid.UUID(document_id),
            attempt=attempt,
            max_attempts=INGEST_MAX_TRIES,
        )
    except TransientIngestionError as exc:
        raise Retry(defer=retry_delay(attempt)) from exc