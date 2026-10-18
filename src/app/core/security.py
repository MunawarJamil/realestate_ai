from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any
import uuid

import jwt

API_KEY_PREFIX = "rk_live_"
WIDGET_KEY_PREFIX = "wk_live_"
VISITOR_TOKEN_ALGORITHM = "HS256"
DEFAULT_VISITOR_TOKEN_EXPIRE_DAYS = 7


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Returns (raw_key, key_hash, key_prefix)."""
    raw_key = f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
    return raw_key, hash_api_key(raw_key), raw_key[:12]


def generate_widget_key() -> str:
    """Generates a public embeddable widget key (e.g. wk_live_...)."""
    return f"{WIDGET_KEY_PREFIX}{secrets.token_urlsafe(24)}"


def create_visitor_token(
    *,
    tenant_id: str | uuid.UUID,
    visitor_id: str | uuid.UUID,
    secret_key: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Creates a signed, expiring JWT visitor session token."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=DEFAULT_VISITOR_TOKEN_EXPIRE_DAYS))
    payload: dict[str, Any] = {
        "sub": str(visitor_id),
        "tenant_id": str(tenant_id),
        "type": "visitor_session",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, secret_key, algorithm=VISITOR_TOKEN_ALGORITHM)


def decode_visitor_token(token: str, secret_key: str) -> dict[str, Any]:
    """Decodes and validates a visitor session JWT token."""
    return jwt.decode(
        token,
        secret_key,
        algorithms=[VISITOR_TOKEN_ALGORITHM],
        options={"require": ["sub", "tenant_id", "type", "exp"]},
    )