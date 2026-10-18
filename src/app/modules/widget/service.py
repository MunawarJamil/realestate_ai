"""Service layer for widget session lifecycle and visitor isolation."""

from datetime import datetime, timedelta, timezone
import uuid

from app.core.security import (
    DEFAULT_VISITOR_TOKEN_EXPIRE_DAYS,
    create_visitor_token,
)
from app.modules.tenants.models import Tenant
from app.modules.widget.schemas import WidgetSessionResponse


class WidgetService:
    def __init__(self, secret_key: str) -> None:
        self._secret_key = secret_key

    def create_or_resume_session(
        self,
        *,
        tenant: Tenant,
        requested_visitor_id: uuid.UUID | None = None,
        expires_delta: timedelta | None = None,
    ) -> WidgetSessionResponse:
        visitor_id = requested_visitor_id or uuid.uuid4()
        effective_delta = expires_delta or timedelta(days=DEFAULT_VISITOR_TOKEN_EXPIRE_DAYS)
        expires_at = datetime.now(timezone.utc) + effective_delta

        token = create_visitor_token(
            tenant_id=tenant.id,
            visitor_id=visitor_id,
            secret_key=self._secret_key,
            expires_delta=effective_delta,
        )

        return WidgetSessionResponse(
            visitor_token=token,
            visitor_id=visitor_id,
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            expires_at=expires_at,
        )
