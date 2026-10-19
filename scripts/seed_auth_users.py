"""Seeds default auth users: Platform Super Admin and Agency Admin/Agent for demo tenant."""

import asyncio

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import get_sessionmaker
from app.modules.auth.models import User, UserRole
from app.modules.tenants.models import Tenant

PLATFORM_ADMIN_EMAIL = "admin@platform.internal"
PLATFORM_ADMIN_PASSWORD = "SuperAdminPassword123!"  # noqa: S105

AGENCY_ADMIN_EMAIL = "admin@prestige.com"
AGENCY_ADMIN_PASSWORD = "AgencyAdminPassword123!"  # noqa: S105

AGENCY_AGENT_EMAIL = "agent@prestige.com"
AGENCY_AGENT_PASSWORD = "AgentPassword123!"  # noqa: S105


async def seed_users() -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        # 1. Platform Super Admin
        res = await session.execute(
            select(User).where(
                User.tenant_id.is_(None),
                User.email == PLATFORM_ADMIN_EMAIL,
            )
        )
        super_admin = res.scalar_one_or_none()
        if not super_admin:
            super_admin = User(
                email=PLATFORM_ADMIN_EMAIL,
                password_hash=hash_password(PLATFORM_ADMIN_PASSWORD),
                full_name="Platform Super Administrator",
                role=UserRole.SUPER_ADMIN,
                tenant_id=None,
                is_active=True,
            )
            session.add(super_admin)
            print(f"[OK] Created Platform Super Admin: {PLATFORM_ADMIN_EMAIL}")
        else:
            print(f"[SKIP] Platform Super Admin already exists: {PLATFORM_ADMIN_EMAIL}")

        # 2. Find Demo Tenant
        res_tenant = await session.execute(
            select(Tenant).where(Tenant.slug == "prestige-prime")
        )
        demo_tenant = res_tenant.scalar_one_or_none()
        if not demo_tenant:
            print("[WARN] Demo tenant 'prestige-prime' not found. Run seed_demo_tenant.py first.")
            await session.commit()
            return

        # 3. Agency Admin
        res_agency_admin = await session.execute(
            select(User).where(
                User.tenant_id == demo_tenant.id,
                User.email == AGENCY_ADMIN_EMAIL,
            )
        )
        agency_admin = res_agency_admin.scalar_one_or_none()
        if not agency_admin:
            agency_admin = User(
                email=AGENCY_ADMIN_EMAIL,
                password_hash=hash_password(AGENCY_ADMIN_PASSWORD),
                full_name="Prestige Agency Principal",
                role=UserRole.AGENCY_ADMIN,
                tenant_id=demo_tenant.id,
                is_active=True,
            )
            session.add(agency_admin)
            print(f"[OK] Created Agency Admin: {AGENCY_ADMIN_EMAIL} for tenant {demo_tenant.name}")
        else:
            print(f"[SKIP] Agency Admin already exists: {AGENCY_ADMIN_EMAIL}")

        # 4. Agency Agent
        res_agency_agent = await session.execute(
            select(User).where(
                User.tenant_id == demo_tenant.id,
                User.email == AGENCY_AGENT_EMAIL,
            )
        )
        agency_agent = res_agency_agent.scalar_one_or_none()
        if not agency_agent:
            agency_agent = User(
                email=AGENCY_AGENT_EMAIL,
                password_hash=hash_password(AGENCY_AGENT_PASSWORD),
                full_name="Prestige Senior Agent",
                role=UserRole.AGENT,
                tenant_id=demo_tenant.id,
                is_active=True,
            )
            session.add(agency_agent)
            print(f"[OK] Created Agency Agent: {AGENCY_AGENT_EMAIL} for tenant {demo_tenant.name}")
        else:
            print(f"[SKIP] Agency Agent already exists: {AGENCY_AGENT_EMAIL}")

        await session.commit()
        print("[SUCCESS] All auth users seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed_users())
