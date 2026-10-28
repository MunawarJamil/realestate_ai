class LeadError(Exception):
    """Base exception for leads domain."""


class LeadNotFoundError(LeadError):
    """Raised when a lead is not found within the tenant's workspace."""


class LeadValidationError(LeadError):
    """Raised when lead data or constraints are invalid."""


class InvalidLeadStatusTransitionError(LeadError):
    """Raised when an illegal status transition is attempted."""
