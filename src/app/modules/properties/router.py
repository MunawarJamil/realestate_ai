from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Final, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.modules.properties.dependencies import get_property_service
from app.modules.properties.enums import PropertyListingType, PropertyStatus, PropertyType
from app.modules.properties.exceptions import PropertyError, PropertyNotFoundError
from app.modules.properties.schemas import (
    PropertyCreate,
    PropertyListResponse,
    PropertyRead,
    PropertyUpdate,
)
from app.modules.properties.service import PropertyService
from app.modules.tenants.dependencies import get_current_tenant
from app.modules.tenants.models import Tenant

router = APIRouter(prefix="/properties", tags=["properties"])

_STATUS_BY_ERROR: Final[tuple[tuple[type[PropertyError], int], ...]] = (
    (PropertyNotFoundError, status.HTTP_404_NOT_FOUND),
)


def _raise_http(exc: PropertyError) -> NoReturn:
    for error_cls, status_code in _STATUS_BY_ERROR:
        if isinstance(exc, error_cls):
            raise HTTPException(status_code=status_code, detail=str(exc))
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "",
    response_model=PropertyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new property listing",
)
async def create_property(
    body: PropertyCreate,
    tenant: Tenant = Depends(get_current_tenant),
    service: PropertyService = Depends(get_property_service),
) -> PropertyRead:
    try:
        return await service.create_property(tenant_id=tenant.id, data=body)
    except PropertyError as exc:
        _raise_http(exc)


@router.get(
    "",
    response_model=PropertyListResponse,
    summary="List inventory with filters, search, and pagination",
)
async def list_properties(
    status: PropertyStatus | None = Query(None, description="Filter by availability status"),
    property_type: PropertyType | None = Query(None, description="Filter by apartment, villa, etc."),
    listing_type: PropertyListingType | None = Query(None, description="sale or rent"),
    min_price: Decimal | None = Query(None, description="Minimum price"),
    max_price: Decimal | None = Query(None, description="Maximum price"),
    location: str | None = Query(None, description="Location search"),
    bedrooms: int | None = Query(None, ge=0, description="Exact bedroom count"),
    search: str | None = Query(None, description="Keyword search in title, address, description"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: str = Query("price", description="Sort field: price, created_at"),
    sort_desc: bool = Query(False, description="Sort descending"),
    tenant: Tenant = Depends(get_current_tenant),
    service: PropertyService = Depends(get_property_service),
) -> PropertyListResponse:
    try:
        return await service.list_properties(
            tenant_id=tenant.id,
            status=status,
            property_type=property_type,
            listing_type=listing_type,
            min_price=min_price,
            max_price=max_price,
            location=location,
            bedrooms=bedrooms,
            search=search,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )
    except PropertyError as exc:
        _raise_http(exc)


@router.get(
    "/{property_id}",
    response_model=PropertyRead,
    summary="Get single property listing",
)
async def get_property(
    property_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    service: PropertyService = Depends(get_property_service),
) -> PropertyRead:
    try:
        return await service.get_property(tenant_id=tenant.id, property_id=property_id)
    except PropertyError as exc:
        _raise_http(exc)


@router.patch(
    "/{property_id}",
    response_model=PropertyRead,
    summary="Update property listing fields or status",
)
async def update_property(
    property_id: uuid.UUID,
    body: PropertyUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    service: PropertyService = Depends(get_property_service),
) -> PropertyRead:
    try:
        return await service.update_property(
            tenant_id=tenant.id,
            property_id=property_id,
            data=body,
        )
    except PropertyError as exc:
        _raise_http(exc)


@router.delete(
    "/{property_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete property listing",
)
async def delete_property(
    property_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    service: PropertyService = Depends(get_property_service),
) -> None:
    try:
        await service.delete_property(tenant_id=tenant.id, property_id=property_id)
    except PropertyError as exc:
        _raise_http(exc)