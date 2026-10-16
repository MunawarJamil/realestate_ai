from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.tenants.models import Tenant
from app.modules.tenants.repository import TenantRepository
from app.modules.tenants.service import TenantService

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_tenant(
    api_key: str | None = Depends(api_key_header),
    session: AsyncSession = Depends(get_session),
) -> Tenant:
    if not api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing API key")

    tenant = await TenantService(TenantRepository(session)).authenticate(api_key)
    if tenant is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    return tenant