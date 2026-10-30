from enum import StrEnum


class BookingStatus(StrEnum):
    PENDING   = "pending"    # Booking created, awaiting agent confirmation
    CONFIRMED = "confirmed"  # Agent confirmed the appointment
    CANCELED  = "canceled"   # Visitor or agent canceled


class BookingSource(StrEnum):
    AI_AGENT  = "ai_agent"   # Created by the autonomous tool
    DASHBOARD = "dashboard"  # Created manually by an agent via dashboard
    API       = "api"        # Created via REST API directly