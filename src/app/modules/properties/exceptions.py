class PropertyError(Exception):
    """Base exception for properties domain."""


class PropertyNotFoundError(PropertyError):
    """Raised when a property is not found within the tenant's workspace."""