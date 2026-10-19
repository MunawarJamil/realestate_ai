import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User, UserRole


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        full_name: str,
        role: UserRole,
        tenant_id: uuid.UUID | None = None,
    ) -> User:
        user = User(
            email=email.strip().lower(),
            password_hash=password_hash,
            full_name=full_name.strip(),
            role=role,
            tenant_id=tenant_id,
            is_active=True,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(
        self, email: str, tenant_id: uuid.UUID | None = None
    ) -> User | None:
        stmt = select(User).where(func.lower(User.email) == email.strip().lower())
        if tenant_id is not None:
            stmt = stmt.where(User.tenant_id == tenant_id)
        else:
            stmt = stmt.where(User.tenant_id.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_agency_user_by_email(self, email: str) -> list[User]:
        """Returns all agency user accounts matching email across tenants."""
        stmt = select(User).where(
            func.lower(User.email) == email.strip().lower(),
            User.role != UserRole.SUPER_ADMIN,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_platform_user_by_email(self, email: str) -> User | None:
        stmt = select(User).where(
            func.lower(User.email) == email.strip().lower(),
            User.role == UserRole.SUPER_ADMIN,
            User.tenant_id.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        *,
        role: UserRole | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[User]:
        stmt = (
            select(User)
            .where(User.tenant_id == tenant_id)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if role is not None:
            stmt = stmt.where(User.role == role)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        user: User,
        *,
        full_name: str | None = None,
        password_hash: str | None = None,
        is_active: bool | None = None,
    ) -> User:
        if full_name is not None:
            user.full_name = full_name.strip()
        if password_hash is not None:
            user.password_hash = password_hash
        if is_active is not None:
            user.is_active = is_active
        await self._session.flush()
        return user

    async def delete(self, user: User) -> None:
        await self._session.delete(user)
        await self._session.flush()
