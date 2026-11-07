from contextvars import ContextVar

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
tenant_id_ctx: ContextVar[str | None] = ContextVar("tenant_id", default=None)


def get_request_id() -> str | None:
    return request_id_ctx.get()


def get_tenant_id() -> str | None:
    return tenant_id_ctx.get()
