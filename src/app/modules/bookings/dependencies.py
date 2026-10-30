from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.bookings.repository import BookingRepository
from app.modules.bookings.service import BookingService


def get_booking_service(
    session: AsyncSession = Depends(get_session),
) -> BookingService:
    return BookingService(repository=BookingRepository(session))