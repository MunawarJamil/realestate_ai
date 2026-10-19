class AuthError(Exception):
    """Base exception for authentication errors."""


class InvalidCredentialsError(AuthError):
    """Raised when email or password is incorrect."""


class CrossRoleForbiddenError(AuthError):
    """Raised when user role attempts to access forbidden login gateway."""


class UserInactiveError(AuthError):
    """Raised when account is suspended or inactive."""


class EmailAlreadyRegisteredError(AuthError):
    """Raised when email is already taken in the tenant or platform."""


class TokenError(AuthError):
    """Raised when JWT token is invalid or expired."""
