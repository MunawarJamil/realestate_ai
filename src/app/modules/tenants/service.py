import secrets
import uuid
from dataclasses import dataclass

from app.core.security import generate_api_key, generate_widget_key, hash_api_key, hash_password
from app.modules.auth.models import User, UserRole
from app.modules.auth.repository import UserRepository
from app.modules.tenants.exceptions import TenantSlugTakenError
from app.modules.tenants.models import Tenant
from app.modules.tenants.repository import TenantRepository


@dataclass(frozen=True)
class TenantWithKey:
    tenant: Tenant
    raw_api_key: str  # Only given at the time of creation, never stored again in db
    admin_email: str | None = None
    admin_password: str | None = None
    admin_user: User | None = None


class TenantService:
    def __init__(
        self,
        repo: TenantRepository,
        user_repo: UserRepository | None = None,
    ) -> None:
        self._repo = repo
        self._user_repo = user_repo

    async def create_tenant(
        self,
        *,
        name: str,
        slug: str,
        allowed_domains: list[str] | None = None,
        admin_email: str | None = None,
        admin_full_name: str | None = None,
        admin_password: str | None = None,
    ) -> TenantWithKey:
        if await self._repo.get_by_slug(slug):
            raise TenantSlugTakenError(slug)

        raw_key, key_hash, key_prefix = generate_api_key()
        widget_key = generate_widget_key()

        tenant = await self._repo.create(
            name=name,
            slug=slug,
            api_key_hash=key_hash,
            api_key_prefix=key_prefix,
            widget_key=widget_key,
            allowed_domains=allowed_domains or [],
        )

        created_admin: User | None = None
        final_admin_password: str | None = None
        if admin_email and self._user_repo:
            clean_email = admin_email.strip().lower()
            final_admin_password = admin_password or secrets.token_urlsafe(12)
            created_admin = await self._user_repo.create(
                email=clean_email,
                password_hash=hash_password(final_admin_password),
                full_name=admin_full_name or f"{name} Administrator",
                role=UserRole.AGENCY_ADMIN,
                tenant_id=tenant.id,
            )

        return TenantWithKey(
            tenant=tenant,
            raw_api_key=raw_key,
            admin_email=admin_email,
            admin_password=final_admin_password,
            admin_user=created_admin,
        )

    async def authenticate(self, raw_api_key: str) -> Tenant | None:
        return await self._repo.get_by_api_key_hash(hash_api_key(raw_api_key))

    async def get_by_widget_key(self, widget_key: str) -> Tenant | None:
        return await self._repo.get_by_widget_key(widget_key)

    async def list_tenants(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        is_active: bool | None = None,
    ) -> list[Tenant]:
        return await self._repo.list_all(
            limit=limit,
            offset=offset,
            is_active=is_active,
        )

    async def update_tenant(
        self,
        tenant_id: uuid.UUID,
        *,
        name: str | None = None,
        allowed_domains: list[str] | None = None,
        is_active: bool | None = None,
    ) -> Tenant | None:
        tenant = await self._repo.get_by_id(tenant_id)
        if tenant is None:
            return None
        return await self._repo.update(
            tenant,
            name=name,
            allowed_domains=allowed_domains,
            is_active=is_active,
        )