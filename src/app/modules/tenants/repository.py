import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tenants.models import Tenant


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        name: str,
        slug: str,
        api_key_hash: str,
        api_key_prefix: str,
        widget_key: str,
        allowed_domains: list[str] | None = None,
    ) -> Tenant:
        tenant = Tenant(
            name=name,
            slug=slug,
            api_key_hash=api_key_hash,
            api_key_prefix=api_key_prefix,
            widget_key=widget_key,
            allowed_domains=allowed_domains or [],
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

    async def get_by_widget_key(self, widget_key: str) -> Tenant | None:
        result = await self._session.execute(
            select(Tenant).where(
                Tenant.widget_key == widget_key, Tenant.is_active.is_(True)
            )
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        is_active: bool | None = None,
    ) -> list[Tenant]:
        stmt = (
            select(Tenant)
            .order_by(Tenant.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if is_active is not None:
            stmt = stmt.where(Tenant.is_active == is_active)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        tenant: Tenant,
        *,
        name: str | None = None,
        allowed_domains: list[str] | None = None,
        is_active: bool | None = None,
    ) -> Tenant:
        if name is not None:
            tenant.name = name
        if allowed_domains is not None:
            tenant.allowed_domains = allowed_domains
        if is_active is not None:
            tenant.is_active = is_active
        await self._session.flush()
        return tenant