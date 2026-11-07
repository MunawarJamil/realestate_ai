import time
from typing import Final
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from sqlalchemy.pool import QueuePool
from starlette.responses import Response

from app.db.session import get_engine

# 1. DB Connection Pool (USE Metrics)
DB_POOL_CHECKED_OUT: Final[Gauge] = Gauge(
    "db_pool_checked_out",
    "Current number of database connections checked out from the pool.",
)
DB_POOL_OVERFLOW: Final[Gauge] = Gauge(
    "db_pool_overflow",
    "Current number of overflow connections in use.",
)
DB_POOL_SIZE: Final[Gauge] = Gauge(
    "db_pool_size",
    "Configured base connection pool size.",
)

# 2. Concurrency & Streaming
ACTIVE_SSE_CONNECTIONS: Final[Gauge] = Gauge(
    "chat_active_sse_connections",
    "Number of currently open, active SSE streaming connections.",
)

# 3. Latency & TTFT (RED Metrics)
CHAT_TTFT_SECONDS: Final[Histogram] = Histogram(
    "chat_ttft_seconds",
    "Time To First Token latency for chat streaming.",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0),
)
HTTP_REQUEST_DURATION_SECONDS: Final[Histogram] = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency by method and path.",
    labelnames=("method", "path", "status_code"),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


def update_db_pool_metrics() -> None:
    """Updates database connection pool gauge values before scrape."""
    try:
        pool = get_engine().sync_engine.pool
        if isinstance(pool, QueuePool):
            DB_POOL_CHECKED_OUT.set(pool.checkedout())
            DB_POOL_OVERFLOW.set(max(0, pool.overflow()))
            DB_POOL_SIZE.set(pool.size())
    except Exception:
        pass


def prometheus_metrics_endpoint() -> Response:
    """FastAPI endpoint handler returning Prometheus text-formatted metrics."""
    update_db_pool_metrics()
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )