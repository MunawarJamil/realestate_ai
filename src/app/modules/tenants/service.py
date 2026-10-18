from dataclasses import dataclass

from app.core.security import generate_api_key, generate_widget_key, hash_api_key
from app.modules.tenants.exceptions import TenantSlugTakenError
from app.modules.tenants.models import Tenant
from app.modules.tenants.repository import TenantRepository


@dataclass(frozen=True)
class TenantWithKey:
    tenant: Tenant
    raw_api_key: str  # Only given at the time of creation, never stored again in db


class TenantService:
    def __init__(self, repo: TenantRepository) -> None:
        self._repo = repo

    async def create_tenant(
        self, *, name: str, slug: str, allowed_domains: list[str] | None = None
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
        return TenantWithKey(tenant=tenant, raw_api_key=raw_key)

    async def authenticate(self, raw_api_key: str) -> Tenant | None:
        return await self._repo.get_by_api_key_hash(hash_api_key(raw_api_key))

    async def get_by_widget_key(self, widget_key: str) -> Tenant | None:
        return await self._repo.get_by_widget_key(widget_key)