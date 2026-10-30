from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timezone

from app.modules.bookings.enums import BookingSource, BookingStatus
from app.modules.bookings.exceptions import (
    BookingNotFoundError,
    BookingRateLimitError,
    InvalidBookingStatusTransitionError,
)
from app.modules.bookings.models import ViewingBooking
from app.modules.bookings.repository import BookingRepository
from app.modules.bookings.schemas import (
    BookingConfirmation,
    BookingCreate,
    BookingListResponse,
    BookingRead,
    BookingUpdate,
)

logger = logging.getLogger(__name__)

MAX_BOOKINGS_PER_DAY = 3

# Valid status transitions
VALID_STATUS_TRANSITIONS: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.PENDING:   {BookingStatus.CONFIRMED, BookingStatus.CANCELED},
    BookingStatus.CONFIRMED: {BookingStatus.CANCELED},
    BookingStatus.CANCELED:  {BookingStatus.PENDING},  # re-open is allowed
}


# ── Socket.IO broadcast helper ────────────────────────────────────────────────

async def _broadcast_booking_event(event_name: str, booking: BookingRead) -> None:
    try:
        from app.modules.chat.socketio_server import sio
        await sio.emit(
            event_name,
            booking.model_dump(mode="json"),
            room=f"tenant_{booking.tenant_id}_agents",
        )
    except Exception as exc:
        logger.warning("Failed to broadcast booking event %s: %r", event_name, exc)


# ── Service ───────────────────────────────────────────────────────────────────

class BookingService:
    """Business operations and lifecycle management for viewing bookings."""

    def __init__(self, repository: BookingRepository) -> None:
        self._repository = repository

    async def create_booking(
        self,
        *,
        tenant_id: uuid.UUID,
        data: BookingCreate,
    ) -> BookingRead:
        # 1. Rate-limit check: max 3 active bookings per visitor phone per day
        daily_count = await self._repository.count_bookings_today(
            tenant_id=tenant_id,
            phone=data.phone,
        )
        if daily_count >= MAX_BOOKINGS_PER_DAY:
            raise BookingRateLimitError(
                f"Visitor with phone '{data.phone}' has reached the daily booking limit "
                f"({MAX_BOOKINGS_PER_DAY} bookings). Please try again tomorrow."
            )

        booking_dict = data.model_dump(exclude_unset=True)
        booking = await self._repository.create(
            tenant_id=tenant_id,
            booking_data=booking_dict,
        )

        logger.info(
            "Booking created id=%s tenant_id=%s visitor=%s preferred_time=%s",
            booking.id,
            tenant_id,
            booking.visitor_name,
            booking.preferred_time.isoformat(),
        )
        booking_read = BookingRead.model_validate(booking)
        await _broadcast_booking_event("booking_created", booking_read)
        return booking_read

    async def get_booking(
        self,
        *,
        tenant_id: uuid.UUID,
        booking_id: uuid.UUID,
    ) -> BookingRead:
        booking = await self._repository.get_by_id(
            tenant_id=tenant_id, booking_id=booking_id
        )
        if not booking:
            raise BookingNotFoundError(f"Booking {booking_id} not found.")
        return BookingRead.model_validate(booking)

    async def list_bookings(
        self,
        *,
        tenant_id: uuid.UUID,
        status: BookingStatus | None = None,
        assigned_agent_id: uuid.UUID | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        search: str | None = None,
        page: int = 1,
        size: int = 20,
        sort_by: str = "preferred_time",
        sort_desc: bool = False,
    ) -> BookingListResponse:
        offset = (page - 1) * size
        bookings, total = await self._repository.list_bookings(
            tenant_id=tenant_id,
            status=status,
            assigned_agent_id=assigned_agent_id,
            from_time=from_time,
            to_time=to_time,
            search=search,
            offset=offset,
            limit=size,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )
        pages = math.ceil(total / size) if size > 0 else 0
        return BookingListResponse(
            items=[BookingRead.model_validate(b) for b in bookings],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    async def update_booking(
        self,
        *,
        tenant_id: uuid.UUID,
        booking_id: uuid.UUID,
        data: BookingUpdate,
    ) -> BookingRead:
        booking = await self._repository.get_by_id(
            tenant_id=tenant_id, booking_id=booking_id
        )
        if not booking:
            raise BookingNotFoundError(f"Booking {booking_id} not found.")

        update_dict = data.model_dump(exclude_unset=True)

        # Validate status transition
        if "status" in update_dict and update_dict["status"] is not None:
            new_status: BookingStatus = update_dict["status"]
            if new_status != booking.status:
                allowed = VALID_STATUS_TRANSITIONS.get(booking.status, set())
                if new_status not in allowed:
                    raise InvalidBookingStatusTransitionError(
                        f"Cannot transition booking from '{booking.status}' to '{new_status}'."
                    )

        updated = await self._repository.update(
            booking=booking, update_data=update_dict
        )
        logger.info("Booking updated id=%s tenant_id=%s", booking_id, tenant_id)

        booking_read = BookingRead.model_validate(updated)
        await _broadcast_booking_event("booking_updated", booking_read)
        return booking_read

    async def cancel_booking(
        self,
        *,
        tenant_id: uuid.UUID,
        booking_id: uuid.UUID,
        reason: str | None = None,
    ) -> BookingRead:
        """Convenience method — sets status to CANCELED and optionally records reason."""
        return await self.update_booking(
            tenant_id=tenant_id,
            booking_id=booking_id,
            data=BookingUpdate(
                status=BookingStatus.CANCELED,
                notes=reason,
            ),
        )

    async def delete_booking(
        self,
        *,
        tenant_id: uuid.UUID,
        booking_id: uuid.UUID,
    ) -> None:
        deleted = await self._repository.delete(
            tenant_id=tenant_id, booking_id=booking_id
        )
        if not deleted:
            raise BookingNotFoundError(f"Booking {booking_id} not found.")
        logger.info("Booking deleted id=%s tenant_id=%s", booking_id, tenant_id)

    # ── Agentic tool helper ───────────────────────────────────────────────────

    async def book_from_agent(
        self,
        *,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        visitor_name: str,
        phone: str,
        preferred_time: datetime,
        property_ref: str | None = None,
        email: str | None = None,
    ) -> BookingConfirmation:
        """High-level method called by the agentic tool

        Returns a `BookingConfirmation` with a ready-made confirmation message
        the AI can relay directly back to the visitor.
        """
        data = BookingCreate(
            visitor_name=visitor_name,
            phone=phone,
            email=email,
            property_ref=property_ref,
            preferred_time=preferred_time,
            conversation_id=conversation_id,
            source=BookingSource.AI_AGENT,
        )
        booking_read = await self.create_booking(tenant_id=tenant_id, data=data)

        # Human-readable confirmation message the agent will send back to visitor
        time_str = booking_read.preferred_time.strftime("%A, %d %B %Y at %I:%M %p UTC")
        prop_info = f" for *{property_ref}*" if property_ref else ""
        message = (
            f"✅ Your viewing{prop_info} has been booked for **{time_str}**. "
            f"Our agent will confirm shortly. "
            f"Your booking reference is `{booking_read.id}`."
        )

        return BookingConfirmation(
            booking_id=booking_read.id,
            status=booking_read.status,
            visitor_name=booking_read.visitor_name,
            preferred_time=booking_read.preferred_time,
            confirmation_message=message,
        )