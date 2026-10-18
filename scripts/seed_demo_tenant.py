"""Seeds or ensures a demo tenant exists with a known widget key for local testing."""

import asyncio

from sqlalchemy import select

from app.core.security import generate_api_key
from app.db.session import get_sessionmaker
from app.modules.tenants.models import Tenant

DEMO_WIDGET_KEY = "wk_live_demo_test_key"
DEMO_SLUG = "prestige-prime"
DEMO_NAME = "Prestige Prime Realty"


async def seed() -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        # Check if already exists
        res = await session.execute(
            select(Tenant).where(
                (Tenant.widget_key == DEMO_WIDGET_KEY) | (Tenant.slug == DEMO_SLUG)
            )
        )
        tenant = res.scalar_one_or_none()

        if tenant:
            tenant.widget_key = DEMO_WIDGET_KEY
            tenant.allowed_domains = ["*"]
            tenant.is_active = True
            await session.commit()
            print(f"[OK] Existing demo tenant updated: {tenant.name}")
            print(f"     Widget Key: {tenant.widget_key}")
            print(f"     Allowed Domains: {tenant.allowed_domains}")
            return

        raw_key, key_hash, key_prefix = generate_api_key()
        tenant = Tenant(
            name=DEMO_NAME,
            slug=DEMO_SLUG,
            api_key_hash=key_hash,
            api_key_prefix=key_prefix,
            widget_key=DEMO_WIDGET_KEY,
            allowed_domains=["*"],
            is_active=True,
        )
        session.add(tenant)
        await session.commit()
        print(f"[OK] Created new demo tenant: {tenant.name}")
        print(f"     Tenant ID:  {tenant.id}")
        print(f"     Widget Key: {tenant.widget_key}")
        print(f"     Raw API Key: {raw_key}")
        print(f"     Allowed Domains: {tenant.allowed_domains}")


if __name__ == "__main__":
    asyncio.run(seed())
