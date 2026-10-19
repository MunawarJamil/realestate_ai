from typing import Final

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import AUDIENCE_AGENCY
from app.db.session import get_session
from app.modules.auth.dependencies import (
    AgencyUserContext,
    get_auth_service,
    get_current_user,
    require_agency_admin,
    require_agency_user,
)
from app.modules.auth.exceptions import (
    AuthError,
    CrossRoleForbiddenError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    TokenError,
    UserInactiveError,
)
from app.modules.auth.models import User, UserRole
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import (
    AuthResponse,
    LoginRequest,
    PlatformLoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
from app.modules.auth.service import AuthService
from app.modules.tenants.repository import TenantRepository

router = APIRouter(prefix="/auth", tags=["auth"])

_ERROR_STATUS_MAP: Final[tuple[tuple[type[AuthError], int], ...]] = (
    (CrossRoleForbiddenError, status.HTTP_403_FORBIDDEN),
    (UserInactiveError, status.HTTP_403_FORBIDDEN),
    (InvalidCredentialsError, status.HTTP_401_UNAUTHORIZED),
    (TokenError, status.HTTP_401_UNAUTHORIZED),
    (EmailAlreadyRegisteredError, status.HTTP_409_CONFLICT),
)


def _handle_auth_error(exc: AuthError) -> None:
    for err_cls, status_code in _ERROR_STATUS_MAP:
        if isinstance(exc, err_cls):
            raise HTTPException(status_code=status_code, detail=str(exc))
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ==============================================================================
# 1. Agency Portal Login Gateway (/login -> app.domain.com)
# ==============================================================================


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Agency Admin & Agent Login (Rejects Super Admin)",
)
async def login_agency_user(
    body: LoginRequest,
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    """Authenticates Agency Admins and Agents.

    Strictly rejects Platform Super Admins with 403 Forbidden.
    """
    try:
        user, tokens = await service.authenticate_agency_user(
            email=body.email,
            password=body.password,
            secret_key=settings.secret_key.get_secret_value(),
            tenant_slug=body.tenant_slug,
        )
    except AuthError as exc:
        _handle_auth_error(exc)
        raise  # unreachable, for type checker

    # Fetch tenant branding metadata
    tenant_name: str | None = None
    tenant_slug: str | None = None
    if user.tenant_id:
        t_repo = TenantRepository(session)
        tenant = await t_repo.get_by_id(user.tenant_id)
        if tenant:
            tenant_name = tenant.name
            tenant_slug = tenant.slug

    return AuthResponse(
        tokens=tokens,
        user=UserRead.model_validate(user),
        tenant_name=tenant_name,
        tenant_slug=tenant_slug,
    )


# ==============================================================================
# 2. Platform Admin Login Gateway (/platform/login -> admin.domain.com)
# ==============================================================================


@router.post(
    "/platform/login",
    response_model=AuthResponse,
    summary="Platform Super Admin Login (Rejects Agency Users)",
)
async def login_platform_user(
    body: PlatformLoginRequest,
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    """Authenticates Platform Super Admins.

    Strictly rejects Agency Admins and Agents with 403 Forbidden.
    """
    try:
        user, tokens = await service.authenticate_platform_user(
            email=body.email,
            password=body.password,
            secret_key=settings.secret_key.get_secret_value(),
        )
    except AuthError as exc:
        _handle_auth_error(exc)
        raise

    return AuthResponse(
        tokens=tokens,
        user=UserRead.model_validate(user),
    )


# ==============================================================================
# 3. Refresh Token Rotation
# ==============================================================================


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token for access token",
)
async def refresh_tokens(
    body: RefreshTokenRequest,
    audience: str = Query(default=AUDIENCE_AGENCY, pattern="^(agency|platform)$"),
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    try:
        return await service.refresh_tokens(
            refresh_token=body.refresh_token,
            secret_key=settings.secret_key.get_secret_value(),
            expected_audience=audience,
        )
    except AuthError as exc:
        _handle_auth_error(exc)
        raise


# ==============================================================================
# 4. User Profile & Agency User Management
# ==============================================================================


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current authenticated user profile",
)
async def get_me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)


@router.get(
    "/users",
    response_model=list[UserRead],
    summary="List team members in current agency workspace",
)
async def list_agency_users(
    context: AgencyUserContext = Depends(require_agency_user),
    session: AsyncSession = Depends(get_session),
    role: UserRole | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[UserRead]:
    repo = UserRepository(session)
    users = await repo.list_by_tenant(
        tenant_id=context.tenant.id,
        role=role,
        limit=limit,
        offset=offset,
    )
    return [UserRead.model_validate(u) for u in users]


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Agency Admin invites/creates new agent",
)
async def create_agent(
    payload: UserCreate,
    context: AgencyUserContext = Depends(require_agency_admin),
    service: AuthService = Depends(get_auth_service),
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    # Agency Admin can only create Agents or co-admins within their tenant
    if payload.role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create a Platform Super Admin from an Agency workspace.",
        )

    try:
        user = await service.create_user(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            role=payload.role,
            tenant_id=context.tenant.id,
        )
        await session.commit()
        return UserRead.model_validate(user)
    except AuthError as exc:
        _handle_auth_error(exc)
        raise
