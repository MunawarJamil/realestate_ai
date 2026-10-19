import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

API_KEY_PREFIX = "rk_live_"
WIDGET_KEY_PREFIX = "wk_live_"
VISITOR_TOKEN_ALGORITHM = "HS256"  # noqa: S105
USER_TOKEN_ALGORITHM = "HS256"  # noqa: S105
DEFAULT_VISITOR_TOKEN_EXPIRE_DAYS = 7
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 14

AUDIENCE_PLATFORM = "platform"
AUDIENCE_AGENCY = "agency"

_hasher = PasswordHasher()


# ==============================================================================
# 1. Password Hashing (Argon2id)
# ==============================================================================


def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2id."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against an Argon2id hash."""
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# ==============================================================================
# 2. API Key Management
# ==============================================================================


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Returns (raw_key, key_hash, key_prefix)."""
    raw_key = f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
    return raw_key, hash_api_key(raw_key), raw_key[:12]


def generate_widget_key() -> str:
    """Generates a public embeddable widget key (e.g. wk_live_...)."""
    return f"{WIDGET_KEY_PREFIX}{secrets.token_urlsafe(24)}"


# ==============================================================================
# 3. Visitor Session Tokens
# ==============================================================================


def create_visitor_token(
    *,
    tenant_id: str | uuid.UUID,
    visitor_id: str | uuid.UUID,
    secret_key: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Creates a signed, expiring JWT visitor session token."""
    now = datetime.now(UTC)
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


# ==============================================================================
# 4. Multi-Tenant User JWT Tokens (Audience & Role Segregated)
# ==============================================================================


def create_user_tokens(
    *,
    user_id: str | uuid.UUID,
    role: str,
    audience: str,  # "platform" or "agency"
    secret_key: str,
    tenant_id: str | uuid.UUID | None = None,
    access_expires_delta: timedelta | None = None,
    refresh_expires_delta: timedelta | None = None,
) -> tuple[str, str]:
    """Issues (access_token, refresh_token) with strict audience and role segregation."""
    now = datetime.now(UTC)
    acc_expire = now + (
        access_expires_delta or timedelta(minutes=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    ref_expire = now + (
        refresh_expires_delta or timedelta(days=DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS)
    )

    access_payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "aud": audience,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(acc_expire.timestamp()),
    }
    if tenant_id is not None:
        access_payload["tenant_id"] = str(tenant_id)

    refresh_payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "aud": audience,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(ref_expire.timestamp()),
    }
    if tenant_id is not None:
        refresh_payload["tenant_id"] = str(tenant_id)

    access_token = jwt.encode(access_payload, secret_key, algorithm=USER_TOKEN_ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, secret_key, algorithm=USER_TOKEN_ALGORITHM)
    return access_token, refresh_token


def decode_user_token(
    token: str,
    secret_key: str,
    expected_audience: str | None = None,
    expected_type: str = "access",
) -> dict[str, Any]:
    """Decodes and validates a user JWT token, enforcing audience and token type."""
    require_keys = ["sub", "type", "exp", "role"]
    decode_options: dict[str, Any] = {"require": require_keys}
    if not expected_audience:
        decode_options["verify_aud"] = False
    else:
        require_keys.append("aud")

    payload: dict[str, Any] = jwt.decode(
        token,
        secret_key,
        algorithms=[USER_TOKEN_ALGORITHM],
        audience=expected_audience,
        options=decode_options,  # type: ignore[arg-type]
    )

    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(
            f"Expected token type '{expected_type}', got '{payload.get('type')}'"
        )

    return payload