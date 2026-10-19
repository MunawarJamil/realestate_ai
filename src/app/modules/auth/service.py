import uuid
from typing import Final

from app.core.security import (
    AUDIENCE_AGENCY,
    AUDIENCE_PLATFORM,
    create_user_tokens,
    decode_user_token,
    hash_password,
    verify_password,
)
from app.modules.auth.exceptions import (
    CrossRoleForbiddenError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    TokenError,
    UserInactiveError,
)
from app.modules.auth.models import User, UserRole
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import TokenResponse
from app.modules.tenants.repository import TenantRepository

TOKEN_LIFETIME_SECONDS: Final[int] = 3600


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        tenant_repo: TenantRepository | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._tenant_repo = tenant_repo

    async def authenticate_agency_user(
        self,
        *,
        email: str,
        password: str,
        secret_key: str,
        tenant_slug: str | None = None,
    ) -> tuple[User, TokenResponse]:
        """Authenticates an Agency Admin or Agent. Rejects Super Admins with 403 Forbidden."""
        clean_email = email.strip().lower()

        # 1. Check if this is a Platform Super Admin attempting to login here
        platform_user = await self._user_repo.get_platform_user_by_email(clean_email)
        if platform_user and verify_password(password, platform_user.password_hash):
            raise CrossRoleForbiddenError(
                "Platform Super Admins cannot sign in via the Agency portal. "
                "Please use the restricted Platform gateway."
            )

        # 2. Resolve tenant if slug provided
        tenant_id: uuid.UUID | None = None
        if tenant_slug and self._tenant_repo:
            tenant = await self._tenant_repo.get_by_slug(tenant_slug)
            if tenant:
                tenant_id = tenant.id

        # 3. Look up matching agency user
        agency_users = await self._user_repo.get_agency_user_by_email(clean_email)
        if not agency_users:
            raise InvalidCredentialsError("Invalid email or password.")

        # If multiple tenants, match by tenant_id or pick first valid password match
        user: User | None = None
        if tenant_id is not None:
            user = next((u for u in agency_users if u.tenant_id == tenant_id), None)
        else:
            for candidate in agency_users:
                if verify_password(password, candidate.password_hash):
                    user = candidate
                    break

        if not user or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")

        if not user.is_active:
            raise UserInactiveError(
                "Your agency account has been deactivated. Contact your administrator."
            )

        # 4. Issue Agency-Audience JWT Tokens
        access_token, refresh_token = create_user_tokens(
            user_id=user.id,
            role=user.role.value,
            audience=AUDIENCE_AGENCY,
            secret_key=secret_key,
            tenant_id=user.tenant_id,
        )

        tokens = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",  # noqa: S106
            expires_in=TOKEN_LIFETIME_SECONDS,
        )
        return user, tokens

    async def authenticate_platform_user(
        self,
        *,
        email: str,
        password: str,
        secret_key: str,
    ) -> tuple[User, TokenResponse]:
        """Authenticates a Platform Super Admin. Rejects Agency users with 403 Forbidden."""
        clean_email = email.strip().lower()

        # 1. Check if this is an agency user attempting platform access
        agency_users = await self._user_repo.get_agency_user_by_email(clean_email)
        if agency_users:
            for u in agency_users:
                if verify_password(password, u.password_hash):
                    raise CrossRoleForbiddenError(
                        "Agency users cannot sign in via the Platform Super Admin gateway. "
                        "Please use the Agency portal."
                    )

        # 2. Look up platform super admin
        user = await self._user_repo.get_platform_user_by_email(clean_email)
        if not user or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid platform administrator credentials.")

        if not user.is_active:
            raise UserInactiveError("Platform administrator account is suspended.")

        # 3. Issue Platform-Audience JWT Tokens
        access_token, refresh_token = create_user_tokens(
            user_id=user.id,
            role=user.role.value,
            audience=AUDIENCE_PLATFORM,
            secret_key=secret_key,
            tenant_id=None,
        )

        tokens = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",  # noqa: S106
            expires_in=TOKEN_LIFETIME_SECONDS,
        )
        return user, tokens

    async def refresh_tokens(
        self,
        *,
        refresh_token: str,
        secret_key: str,
        expected_audience: str,
    ) -> TokenResponse:
        """Rotates refresh token and issues fresh access token."""
        try:
            payload = decode_user_token(
                token=refresh_token,
                secret_key=secret_key,
                expected_audience=expected_audience,
                expected_type="refresh",
            )
        except Exception as exc:
            raise TokenError("Invalid or expired refresh token.") from exc

        user_id = uuid.UUID(payload["sub"])
        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise UserInactiveError("User account no longer active.")

        new_access, new_refresh = create_user_tokens(
            user_id=user.id,
            role=user.role.value,
            audience=expected_audience,
            secret_key=secret_key,
            tenant_id=user.tenant_id,
        )

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type="bearer",  # noqa: S106
            expires_in=TOKEN_LIFETIME_SECONDS,
        )

    async def create_user(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        role: UserRole,
        tenant_id: uuid.UUID | None = None,
    ) -> User:
        """Creates a new user with password hashing and duplicate checks."""
        clean_email = email.strip().lower()

        # Check existing
        existing = await self._user_repo.get_by_email(clean_email, tenant_id=tenant_id)
        if existing:
            raise EmailAlreadyRegisteredError(
                f"A user with email '{clean_email}' already exists in this workspace."
            )

        hashed = hash_password(password)
        return await self._user_repo.create(
            email=clean_email,
            password_hash=hashed,
            full_name=full_name,
            role=role,
            tenant_id=tenant_id,
        )
