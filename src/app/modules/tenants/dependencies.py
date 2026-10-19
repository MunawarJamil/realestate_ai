import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import AUDIENCE_AGENCY, decode_user_token
from app.db.session import get_session
from app.modules.tenants.models import Tenant
from app.modules.tenants.repository import TenantRepository
from app.modules.tenants.service import TenantService

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer_auth = HTTPBearer(auto_error=False)


async def get_current_tenant(
    api_key: str | None = Depends(api_key_header),
    auth: HTTPAuthorizationCredentials | None = Depends(_bearer_auth),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> Tenant:
    """Authenticates tenant context via either Agency JWT Bearer token OR X-API-Key header."""
    # 1. Agency JWT Bearer Token (Agency Admin / Agent logged in via portal)
    if auth and auth.credentials:
        try:
            payload = decode_user_token(
                token=auth.credentials,
                secret_key=settings.secret_key.get_secret_value(),
                expected_audience=AUDIENCE_AGENCY,
                expected_type="access",
            )
            raw_tenant_id = payload.get("tenant_id")
            if raw_tenant_id:
                tenant_id = uuid.UUID(raw_tenant_id)
                tenant = await TenantRepository(session).get_by_id(tenant_id)
                if tenant:
                    if not tenant.is_active:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Agency tenant account has been deactivated.",
                        )
                    return tenant
        except HTTPException:
            raise
        except (jwt.PyJWTError, ValueError):
            pass

    # 2. X-API-Key Header (Direct API key authentication)
    if api_key:
        tenant = await TenantService(TenantRepository(session)).authenticate(api_key)
        if tenant:
            if not tenant.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Agency tenant account has been deactivated.",
                )
            return tenant

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=(
            "Authentication required. Provide a valid 'Authorization: Bearer <token>' "
            "or 'X-API-Key'."
        ),
        headers={"WWW-Authenticate": "Bearer"},
    )