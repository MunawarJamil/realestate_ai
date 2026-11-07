import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.request_context import request_id_ctx, tenant_id_ctx

import structlog

# LogRecord ki built-in attributes, taake "extra" fields alag nikal sakein
_RESERVED = set(logging.makeLogRecord({}).__dict__) | {
    "message",
    "asctime",
    "request_id",
    "tenant_id",
}


class RequestContextFilter(logging.Filter):
    """Har log record par request_id / tenant_id lagata hai."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or "-"
        record.tenant_id = tenant_id_ctx.get() or "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "tenant_id": getattr(record, "tenant_id", "-"),
        }
        payload.update(
            {k: v for k, v in record.__dict__.items() if k not in _RESERVED}
        )
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _structlog_request_context(
    logger: Any, method_name: str, event_dict: structlog.typing.EventDict
) -> structlog.typing.EventDict:
    event_dict["request_id"] = request_id_ctx.get() or "-"
    event_dict["tenant_id"] = tenant_id_ctx.get() or "-"
    return event_dict


def configure_logging(log_level: str, *, json_logs: bool) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestContextFilter())
    handler.setFormatter(
        JsonFormatter()
        if json_logs
        else logging.Formatter(
            "%(asctime)s %(levelname)s [%(request_id)s] [%(tenant_id)s] %(name)s: %(message)s"
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level.upper())

    # uvicorn ke apne handlers hata do, sab root ke through jaye
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True
    # access log hum khud middleware se likhte hain (duration ke sath)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # structlog configuration (taake structlog.get_logger() bhi same context capture kare)
    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        _structlog_request_context,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
