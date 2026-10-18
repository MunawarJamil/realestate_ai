"""FastAPI dependencies for public widget authentication and visitor sessions."""

from dataclasses import dataclass
import uuid

from fastapi import Depends, Header, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import decode_visitor_token
from app.db.session import get_session
from app.modules.tenants.models import Tenant
from app.modules.tenants.repository import TenantRepository
from app.modules.widget.security import is_origin_allowed

_bearer_auth = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class VisitorContext:
    """Authenticated visitor context providing tenant and visitor isolation."""

    visitor_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant: Tenant


async def get_widget_tenant(
    x_widget_key: str | None = Header(None, alias="X-Widget-Key"),
    widget_key: str | None = Query(None, alias="widget_key"),
    origin: str | None = Header(None, alias="Origin"),
    referer: str | None = Header(None, alias="Referer"),
    session: AsyncSession = Depends(get_session),
) -> Tenant:
    """Validates public widget key and HTTP Origin against tenant allowed_domains."""
    key = x_widget_key or widget_key
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing widget key. Provide 'X-Widget-Key' header or 'widget_key' parameter.",
        )

    repo = TenantRepository(session)
    tenant = await repo.get_by_widget_key(key)
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive widget key.",
        )

    # Origin header takes precedence; fallback to Referer if behind certain proxies/embeds
    effective_origin = origin or referer
    if not is_origin_allowed(effective_origin, tenant.allowed_domains):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Origin '{effective_origin}' is not authorized to host this widget.",
        )

    return tenant


async def get_current_visitor(
    auth: HTTPAuthorizationCredentials | None = Depends(_bearer_auth),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> VisitorContext:
    """Authenticates and verifies the visitor session Bearer JWT."""
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing visitor session token. Provide 'Authorization: Bearer <token>'.",
        )

    try:
        payload = decode_visitor_token(
            token=auth.credentials,
            secret_key=settings.secret_key.get_secret_value(),
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Visitor session token has expired.",
        ) from exc
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid visitor session token.",
        ) from exc

    if payload.get("type") != "visitor_session":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token type is not a valid visitor session.",
        )

    try:
        visitor_id = uuid.UUID(payload["sub"])
        tenant_id = uuid.UUID(payload["tenant_id"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed visitor session claims.",
        ) from exc

    repo = TenantRepository(session)
    tenant = await repo.get_by_id(tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant is inactive or not found.",
        )

    return VisitorContext(
        visitor_id=visitor_id,
        tenant_id=tenant_id,
        tenant=tenant,
    )
