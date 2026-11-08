import json
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

    # async def authenticate(self, raw_api_key: str) -> Tenant | None:
    #     return await self._repo.get_by_api_key_hash(hash_api_key(raw_api_key))

    async def authenticate(self, raw_api_key: str) -> Tenant | None:
        if not raw_api_key.startswith("rk_live_"):
            return None

        key_hash = hash_api_key(raw_api_key)

        # 1. Try Redis cache first (Completely bypasses Postgres for streaming requests)
        try:
            from app.modules.chat.redis_pubsub import get_redis_client

            redis = get_redis_client()
            if redis is not None:
                cached = await redis.get(f"auth:tenant:hash:{key_hash}")
                if cached:
                    raw_str = cached.decode("utf-8") if isinstance(cached, bytes) else str(cached)
                    data = json.loads(raw_str)
                    if not data.get("is_active", True):
                        return None
                    return Tenant(
                        id=uuid.UUID(data["id"]),
                        name=data["name"],
                        slug=data["slug"],
                        api_key_hash=data["api_key_hash"],
                        api_key_prefix=data["api_key_prefix"],
                        widget_key=data["widget_key"],
                        allowed_domains=data.get("allowed_domains", []),
                        is_active=data.get("is_active", True),
                    )
        except Exception:
            pass  # Fall back to database lookup gracefully

        # 2. Database Lookup via self._repo
        tenant = await self._repo.get_by_api_key_hash(key_hash)
        if tenant is None or not tenant.is_active:
            return None

        # 3. Cache full tenant in Redis for 60 seconds
        try:
            from app.modules.chat.redis_pubsub import get_redis_client

            redis = get_redis_client()
            if redis is not None:
                payload = json.dumps(
                    {
                        "id": str(tenant.id),
                        "name": tenant.name,
                        "slug": tenant.slug,
                        "api_key_hash": tenant.api_key_hash,
                        "api_key_prefix": tenant.api_key_prefix,
                        "widget_key": tenant.widget_key,
                        "allowed_domains": tenant.allowed_domains,
                        "is_active": tenant.is_active,
                    }
                )
                await redis.set(f"auth:tenant:hash:{key_hash}", payload, ex=60)
        except Exception:
            pass

        return tenant




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