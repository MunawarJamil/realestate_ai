import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import (
    AUDIENCE_AGENCY,
    AUDIENCE_PLATFORM,
    decode_user_token,
)
from app.db.session import get_session
from app.modules.auth.models import User, UserRole
from app.modules.auth.repository import UserRepository
from app.modules.auth.service import AuthService
from app.modules.tenants.models import Tenant
from app.modules.tenants.repository import TenantRepository

_bearer_auth = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AgencyUserContext:
    user: User
    tenant: Tenant


def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(
        user_repo=UserRepository(session),
        tenant_repo=TenantRepository(session),
    )


async def get_current_user(
    auth: HTTPAuthorizationCredentials | None = Depends(_bearer_auth),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Authenticates any active user (Platform Admin, Agency Admin, or Agent)."""
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token. Provide 'Authorization: Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_user_token(
            token=auth.credentials,
            secret_key=settings.secret_key.get_secret_value(),
            expected_type="access",
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = uuid.UUID(payload["sub"])
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated or not found.",
        )

    return user


async def require_platform_admin(
    auth: HTTPAuthorizationCredentials | None = Depends(_bearer_auth),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Enforces aud='platform' and role='super_admin'."""
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Platform authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_user_token(
            token=auth.credentials,
            secret_key=settings.secret_key.get_secret_value(),
            expected_audience=AUDIENCE_PLATFORM,
            expected_type="access",
        )
    except jwt.InvalidAudienceError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token audience invalid. Agency tokens cannot access platform endpoints.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired platform token.",
        ) from exc

    if payload.get("role") != UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Super Admin role required.",
        )

    user_id = uuid.UUID(payload["sub"])
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active or user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator privileges revoked or inactive.",
        )

    return user


async def require_agency_user(
    auth: HTTPAuthorizationCredentials | None = Depends(_bearer_auth),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> AgencyUserContext:
    """Enforces aud='agency' and returns user + isolated tenant context."""
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agency authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_user_token(
            token=auth.credentials,
            secret_key=settings.secret_key.get_secret_value(),
            expected_audience=AUDIENCE_AGENCY,
            expected_type="access",
        )
    except jwt.InvalidAudienceError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token audience invalid. Platform tokens cannot access agency endpoints.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired agency token.",
        ) from exc

    if payload.get("role") not in [UserRole.AGENCY_ADMIN.value, UserRole.AGENT.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Agency member role required.",
        )

    raw_tenant_id = payload.get("tenant_id")
    if not raw_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token missing tenant isolation context.",
        )

    user_id = uuid.UUID(payload["sub"])
    tenant_id = uuid.UUID(raw_tenant_id)

    user_repo = UserRepository(session)
    tenant_repo = TenantRepository(session)

    user = await user_repo.get_by_id(user_id)
    if not user or not user.is_active or user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agency user account is deactivated or invalid.",
        )

    tenant = await tenant_repo.get_by_id(tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agency workspace has been suspended or is inactive.",
        )

    return AgencyUserContext(user=user, tenant=tenant)


async def require_agency_admin(
    context: AgencyUserContext = Depends(require_agency_user),
) -> AgencyUserContext:
    """Enforces that the caller is specifically an Agency Admin (e.g. for user management)."""
    if context.user.role != UserRole.AGENCY_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agency Administrator role required for this operation.",
        )
    return context
