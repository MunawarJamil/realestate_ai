"""Domain exceptions for widget authentication and sessions."""


class WidgetError(Exception):
    """Base class for all widget errors."""


class MissingWidgetKeyError(WidgetError):
    def __init__(self, message: str = "Missing X-Widget-Key header") -> None:
        super().__init__(message)


class InvalidWidgetKeyError(WidgetError):
    def __init__(self, message: str = "Invalid or inactive widget key") -> None:
        super().__init__(message)


class OriginNotAllowedError(WidgetError):
    def __init__(self, origin: str | None = None) -> None:
        message = f"Origin '{origin}' is not authorized for this widget key" if origin else "Unauthorized origin"
        super().__init__(message)


class MissingVisitorTokenError(WidgetError):
    def __init__(self, message: str = "Missing visitor authentication token") -> None:
        super().__init__(message)


class InvalidVisitorTokenError(WidgetError):
    def __init__(self, message: str = "Invalid visitor session token") -> None:
        super().__init__(message)


class VisitorTokenExpiredError(WidgetError):
    def __init__(self, message: str = "Visitor session token has expired") -> None:
        super().__init__(message)
