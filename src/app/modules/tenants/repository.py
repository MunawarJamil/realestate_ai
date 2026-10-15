import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tenants.models import Tenant


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, name: str, slug: str, api_key_hash: str, api_key_prefix: str
    ) -> Tenant:
        tenant = Tenant(
            name=name,
            slug=slug,
            api_key_hash=api_key_hash,
            api_key_prefix=api_key_prefix,
        )
        self._session.add(tenant)
        await self._session.flush()  # DB se id/defaults mil jaate hain, commit nahi hota
        return tenant

    async def get_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        return await self._session.get(Tenant, tenant_id)

    async def get_by_slug(self, slug: str) -> Tenant | None:
        result = await self._session.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_api_key_hash(self, api_key_hash: str) -> Tenant | None:
        result = await self._session.execute(
            select(Tenant).where(
                Tenant.api_key_hash == api_key_hash, Tenant.is_active.is_(True)
            )
        )
        return result.scalar_one_or_none()