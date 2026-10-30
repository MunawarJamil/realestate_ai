"""schedule_viewing: Agentic tool for booking property viewings.

This is the callable that the LangGraph tool) will invoke.
It is intentionally decoupled from FastAPI — it manages its own DB session
so it can run inside a LangGraph node without a request context.

Usage by the LangGraph tool executor:
    result = await schedule_viewing(
        tenant_id=uuid.UUID("..."),
        conversation_id=uuid.UUID("..."),
        visitor_name="Ahmed Al-Rashid",
        phone="+971501234567",
        preferred_time=datetime(2026, 11, 5, 14, 0, tzinfo=timezone.utc),
        property_ref="Palm Jumeirah Villa - 5BR",
    )
    # result.confirmation_message → relay to visitor
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from app.db.session import get_sessionmaker
from app.modules.bookings.exceptions import BookingError, BookingRateLimitError
from app.modules.bookings.repository import BookingRepository
from app.modules.bookings.schemas import BookingConfirmation
from app.modules.bookings.service import BookingService

logger = logging.getLogger(__name__)


async def schedule_viewing(
    *,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    visitor_name: str,
    phone: str,
    preferred_time: datetime,
    property_ref: str | None = None,
    email: str | None = None,
) -> BookingConfirmation:
    """Autonomous agentic tool — books a property viewing from the AI agent.

    Args:
        tenant_id:       The tenant this booking belongs to (from graph state).
        conversation_id: The active conversation UUID (from graph state).
        visitor_name:    Full name of the visitor requesting the viewing.
        phone:           Visitor's contact number (7–15 digits, optional '+' prefix).
        preferred_time:  Desired datetime for the viewing (must be future, UTC-aware).
        property_ref:    Free-text property identifier (address, listing title, or ID).
        email:           Optional visitor email address.

    Returns:
        BookingConfirmation with:
            - booking_id: UUID of the created booking record.
            - status: BookingStatus.PENDING.
            - visitor_name: Echo of the provided name.
            - preferred_time: Confirmed slot.
            - confirmation_message: Ready-made human-readable message to relay to the visitor.

    Raises:
        BookingRateLimitError: Visitor exceeded 3 bookings/day — agent should apologise
                               and suggest the visitor call the office directly.
        BookingError:          Any other domain-level booking failure.
        ValueError:            If phone format or preferred_time validation fails (Pydantic).
    """
    session_factory = get_sessionmaker()

    async with session_factory() as session:
        try:
            service = BookingService(repository=BookingRepository(session))
            confirmation = await service.book_from_agent(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                visitor_name=visitor_name,
                phone=phone,
                preferred_time=preferred_time,
                property_ref=property_ref,
                email=email,
            )
            await session.commit()
            logger.info(
                "schedule_viewing tool: booking created id=%s tenant=%s conversation=%s",
                confirmation.booking_id,
                tenant_id,
                conversation_id,
            )
            return confirmation

        except BookingRateLimitError:
            await session.rollback()
            raise

        except BookingError:
            await session.rollback()
            raise

        except Exception:
            await session.rollback()
            logger.exception(
                "schedule_viewing tool: unexpected error tenant=%s conversation=%s",
                tenant_id,
                conversation_id,
            )
            raise


# ── Tool metadata (used by the LangGraph tool registry in Phase 14.4) ─────────

TOOL_NAME = "schedule_viewing"
TOOL_DESCRIPTION = (
    "Books a property viewing appointment for a visitor. "
    "Use this tool when the visitor explicitly asks to schedule, book, or arrange "
    "a viewing or site visit for a specific property. "
    "Always confirm visitor_name, phone, and preferred_time before calling this tool."
)