from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Final, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.modules.bookings.dependencies import get_booking_service
from app.modules.bookings.enums import BookingStatus
from app.modules.bookings.exceptions import (
    BookingError,
    BookingNotFoundError,
    BookingRateLimitError,
    InvalidBookingStatusTransitionError,
)
from app.modules.bookings.schemas import (
    BookingCreate,
    BookingListResponse,
    BookingRead,
    BookingUpdate,
)
from app.modules.bookings.service import BookingService
from app.modules.tenants.dependencies import get_current_tenant
from app.modules.tenants.models import Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bookings", tags=["bookings"])

_STATUS_BY_ERROR: Final[tuple[tuple[type[BookingError], int], ...]] = (
    (BookingNotFoundError,                status.HTTP_404_NOT_FOUND),
    (BookingRateLimitError,               status.HTTP_429_TOO_MANY_REQUESTS),
    (InvalidBookingStatusTransitionError, status.HTTP_422_UNPROCESSABLE_ENTITY),
)


def _raise_http(exc: BookingError) -> NoReturn:
    for error_cls, status_code in _STATUS_BY_ERROR:
        if isinstance(exc, error_cls):
            raise HTTPException(status_code=status_code, detail=str(exc))
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ── Inline request models ─────────────────────────────────────────────────────

class AssignBookingRequest(BaseModel):
    assigned_agent_id: uuid.UUID | None = None


class CancelBookingRequest(BaseModel):
    reason: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=BookingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new property viewing booking",
)
async def create_booking(
    body: BookingCreate,
    tenant: Tenant = Depends(get_current_tenant),
    service: BookingService = Depends(get_booking_service),
) -> BookingRead:
    try:
        return await service.create_booking(tenant_id=tenant.id, data=body)
    except BookingError as exc:
        _raise_http(exc)


@router.get(
    "",
    response_model=BookingListResponse,
    summary="List bookings with filtering and pagination",
)
async def list_bookings(
    status: BookingStatus | None = Query(None, description="Filter by booking status"),
    assigned_agent_id: uuid.UUID | None = Query(None, description="Filter by assigned agent"),
    from_time: datetime | None = Query(None, description="Filter bookings on or after this datetime (UTC)"),
    to_time: datetime | None = Query(None, description="Filter bookings on or before this datetime (UTC)"),
    search: str | None = Query(None, description="Search by visitor name, phone, or property ref"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: str = Query("preferred_time", description="Sort field: preferred_time, created_at"),
    sort_desc: bool = Query(False, description="Sort descending"),
    tenant: Tenant = Depends(get_current_tenant),
    service: BookingService = Depends(get_booking_service),
) -> BookingListResponse:
    try:
        return await service.list_bookings(
            tenant_id=tenant.id,
            status=status,
            assigned_agent_id=assigned_agent_id,
            from_time=from_time,
            to_time=to_time,
            search=search,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )
    except BookingError as exc:
        _raise_http(exc)


@router.get(
    "/{booking_id}",
    response_model=BookingRead,
    summary="Get a single booking by ID",
)
async def get_booking(
    booking_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    service: BookingService = Depends(get_booking_service),
) -> BookingRead:
    try:
        return await service.get_booking(tenant_id=tenant.id, booking_id=booking_id)
    except BookingError as exc:
        _raise_http(exc)


@router.patch(
    "/{booking_id}",
    response_model=BookingRead,
    summary="Update booking fields or status",
)
async def update_booking(
    booking_id: uuid.UUID,
    body: BookingUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    service: BookingService = Depends(get_booking_service),
) -> BookingRead:
    try:
        return await service.update_booking(
            tenant_id=tenant.id,
            booking_id=booking_id,
            data=body,
        )
    except BookingError as exc:
        _raise_http(exc)


@router.post(
    "/{booking_id}/assign",
    response_model=BookingRead,
    summary="Assign or reassign a booking to a broker agent",
)
async def assign_booking(
    booking_id: uuid.UUID,
    body: AssignBookingRequest,
    tenant: Tenant = Depends(get_current_tenant),
    service: BookingService = Depends(get_booking_service),
) -> BookingRead:
    try:
        return await service.update_booking(
            tenant_id=tenant.id,
            booking_id=booking_id,
            data=BookingUpdate(assigned_agent_id=body.assigned_agent_id),
        )
    except BookingError as exc:
        _raise_http(exc)


@router.post(
    "/{booking_id}/cancel",
    response_model=BookingRead,
    summary="Cancel a booking with an optional reason",
)
async def cancel_booking(
    booking_id: uuid.UUID,
    body: CancelBookingRequest,
    tenant: Tenant = Depends(get_current_tenant),
    service: BookingService = Depends(get_booking_service),
) -> BookingRead:
    try:
        return await service.cancel_booking(
            tenant_id=tenant.id,
            booking_id=booking_id,
            reason=body.reason,
        )
    except BookingError as exc:
        _raise_http(exc)


@router.delete(
    "/{booking_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete a booking record",
)
async def delete_booking(
    booking_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    service: BookingService = Depends(get_booking_service),
) -> None:
    try:
        await service.delete_booking(tenant_id=tenant.id, booking_id=booking_id)
    except BookingError as exc:
        _raise_http(exc)