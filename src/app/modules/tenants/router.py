import secrets
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.modules.tenants.dependencies import get_current_tenant
from app.modules.tenants.exceptions import TenantSlugTakenError
from app.modules.tenants.models import Tenant
from app.modules.tenants.repository import TenantRepository
from app.modules.tenants.schemas import (
    TenantCreate,
    TenantCreated,
    TenantRead,
    TenantUpdate,
)
from app.modules.tenants.service import TenantService


async def require_admin(
    x_admin_key: str = Header(...),
    settings: Settings = Depends(get_settings),
) -> None:
    if not secrets.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid admin key")


router = APIRouter(prefix="/tenants", tags=["tenants"], dependencies=[Depends(require_admin)])


me_router = APIRouter(prefix="/tenants", tags=["tenants"])


@me_router.get("/me", response_model=TenantRead)
async def read_me(tenant: Tenant = Depends(get_current_tenant)) -> Tenant:
    return tenant


@router.get("", response_model=list[TenantRead])
async def list_tenants(
    limit: int = Query(default=100, ge=1, le=200, description="Max number of tenants to return"),
    offset: int = Query(default=0, ge=0, description="Number of tenants to skip"),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
    session: AsyncSession = Depends(get_session),
) -> list[Tenant]:
    service = TenantService(TenantRepository(session))
    return await service.list_tenants(limit=limit, offset=offset, is_active=is_active)


@router.patch("/{tenant_id}", response_model=TenantRead)
async def update_tenant(
    tenant_id: uuid.UUID,
    payload: TenantUpdate,
    session: AsyncSession = Depends(get_session),
) -> Tenant:
    service = TenantService(TenantRepository(session))
    updated = await service.update_tenant(
        tenant_id=tenant_id,
        name=payload.name,
        allowed_domains=payload.allowed_domains,
        is_active=payload.is_active,
    )
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    await session.commit()
    return updated


@router.post("", response_model=TenantCreated, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    payload: TenantCreate, session: AsyncSession = Depends(get_session)
) -> TenantCreated:
    service = TenantService(TenantRepository(session))
    try:
        result = await service.create_tenant(
            name=payload.name,
            slug=payload.slug,
            allowed_domains=payload.allowed_domains,
        )
        await session.commit()
    except TenantSlugTakenError as err:
        raise HTTPException(status.HTTP_409_CONFLICT, "Slug already taken") from err

    return TenantCreated(
        **TenantRead.model_validate(result.tenant).model_dump(),
        api_key=result.raw_api_key,
    )