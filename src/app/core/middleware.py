import logging
import re
import time
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.request_context import request_id_ctx, tenant_id_ctx

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9_\-]{8,64}$")
_SKIP_ACCESS_LOG = frozenset({"/health", "/metrics"})

access_logger = logging.getLogger("app.access")


class RequestContextMiddleware:
    """Request ID set/propagate karta hai aur har request ka access log likhta hai."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER)
        request_id = (
            incoming
            if incoming and _VALID_REQUEST_ID.fullmatch(incoming)
            else uuid.uuid4().hex
        )
        rid_token = request_id_ctx.set(request_id)
        tid_token = tenant_id_ctx.set(None)
        status_code = 500
        started = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            access_logger.exception("request_failed", extra=self._fields(scope, 500, started))
            raise
        else:
            if scope["path"] not in _SKIP_ACCESS_LOG:
                access_logger.info(
                    "request_completed", extra=self._fields(scope, status_code, started)
                )
        finally:
            tenant_id_ctx.reset(tid_token)
            request_id_ctx.reset(rid_token)

    @staticmethod
    def _fields(scope: Scope, status_code: int, started: float) -> dict[str, object]:
        return {
            "method": scope["method"],
            "path": scope["path"],
            "status_code": status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        }