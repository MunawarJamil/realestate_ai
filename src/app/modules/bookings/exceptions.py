class BookingError(Exception):
    """Base exception for the bookings domain."""


class BookingNotFoundError(BookingError):
    """Raised when a booking is not found within the tenant's workspace."""


class BookingRateLimitError(BookingError):
    """Raised when a visitor exceeds the max allowed bookings per day."""


class InvalidBookingStatusTransitionError(BookingError):
    """Raised when an illegal status transition is attempted."""