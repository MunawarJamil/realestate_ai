"""Security utilities for public widget origin validation and visitor token management."""

from urllib.parse import urlparse


def is_origin_allowed(origin: str | None, allowed_domains: list[str]) -> bool:
    """Validates HTTP Origin against a tenant's configured allowed_domains list.

    Rules:
    - If allowed_domains contains "*", any origin is permitted (e.g., local dev or open embed).
    - If origin is None, empty, or "null", it is rejected unless "*" is in allowed_domains.
    - Matches exact hostname or hostname:port (e.g., "localhost:5173", "app.agency.com").
    - Supports wildcard subdomains (e.g., "*.agency.com" matches "sub.agency.com" and "agency.com").
    - Supports root domain matching (e.g., "agency.com" matches "agency.com" and "www.agency.com").
    """
    if not allowed_domains:
        return False

    cleaned_patterns = [p.strip().lower() for p in allowed_domains if p.strip()]
    if "*" in cleaned_patterns:
        return True

    if not origin or origin.strip().lower() == "null":
        return False

    parsed = urlparse(origin.strip())
    host = (parsed.hostname or "").lower()
    netloc = (parsed.netloc or "").lower()

    if not host:
        return False

    for raw_pattern in cleaned_patterns:
        pattern = raw_pattern
        # Strip scheme if user accidentally supplied one (e.g., "https://agency.com")
        if pattern.startswith("http://"):
            pattern = pattern[7:]
        elif pattern.startswith("https://"):
            pattern = pattern[8:]
        pattern = pattern.rstrip("/")

        # Direct match on netloc (including port, e.g. "localhost:3000") or hostname
        if netloc == pattern or host == pattern:
            return True

        # Wildcard subdomain match (e.g., "*.example.com")
        if pattern.startswith("*."):
            suffix = pattern[2:]
            if host == suffix or host.endswith(f".{suffix}"):
                return True

        # Plain root domain matches root and its subdomains (e.g., "example.com" matches "sub.example.com")
        if host.endswith(f".{pattern}"):
            return True

    return False
