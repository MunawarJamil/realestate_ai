"""Unit tests for widget public authentication, origin validation, and visitor session tokens."""

from datetime import UTC, datetime, timedelta
import uuid

import httpx
import jwt
from pydantic import SecretStr
import pytest
from starlette.requests import Request

from app.core.config import Settings, get_settings
from app.core.security import (
    WIDGET_KEY_PREFIX,
    create_visitor_token,
    decode_visitor_token,
    generate_widget_key,
)
from app.main import create_app
from app.modules.tenants.models import Tenant
from app.modules.widget.dependencies import (
    VisitorContext,
    get_current_visitor,
    get_widget_tenant,
)
from app.modules.widget.router import router as widget_router
from app.modules.widget.schemas import WidgetSessionResponse
from app.modules.widget.security import is_origin_allowed
from app.modules.widget.service import WidgetService

SECRET_KEY = "test-secret-key-for-jwt-signing-and-verification"


def make_tenant(**overrides: object) -> Tenant:
    t = Tenant()
    t.id = overrides.get("id", uuid.uuid4())  # type: ignore[assignment]
    t.name = overrides.get("name", "Prime Properties")  # type: ignore[assignment]
    t.slug = overrides.get("slug", "prime-properties")  # type: ignore[assignment]
    t.api_key_hash = overrides.get("api_key_hash", "hash123")  # type: ignore[assignment]
    t.api_key_prefix = overrides.get("api_key_prefix", "rk_live_12")  # type: ignore[assignment]
    t.widget_key = overrides.get("widget_key", "wk_live_valid123")  # type: ignore[assignment]
    t.allowed_domains = overrides.get("allowed_domains", ["agency.com", "localhost:3000"])  # type: ignore[assignment]
    t.is_active = overrides.get("is_active", True)  # type: ignore[assignment]
    t.created_at = datetime.now(UTC)
    t.updated_at = datetime.now(UTC)
    return t


# ==============================================================================
# 1. Widget Key Generation
# ==============================================================================


def test_generate_widget_key_prefix_and_length() -> None:
    key1 = generate_widget_key()
    key2 = generate_widget_key()

    assert key1.startswith(WIDGET_KEY_PREFIX)
    assert key2.startswith(WIDGET_KEY_PREFIX)
    assert key1 != key2
    assert len(key1) > 20


# ==============================================================================
# 2. Origin Domain Validation
# ==============================================================================


@pytest.mark.parametrize(
    ("origin", "allowed_domains", "expected"),
    [
        # Wildcard allows anything
        ("https://example.com", ["*"], True),
        ("http://localhost:5173", ["*"], True),
        ("null", ["*"], True),
        # Empty allowed list rejects everything
        ("https://example.com", [], False),
        # Exact domain match
        ("https://agency.com", ["agency.com"], True),
        ("http://agency.com", ["agency.com"], True),
        # Port matching
        ("http://localhost:3000", ["localhost:3000"], True),
        ("http://localhost:8080", ["localhost:3000"], False),
        # Subdomain matching with wildcard pattern
        ("https://sub.agency.com", ["*.agency.com"], True),
        ("https://deep.sub.agency.com", ["*.agency.com"], True),
        ("https://agency.com", ["*.agency.com"], True),
        ("https://evilagency.com", ["*.agency.com"], False),
        # Root pattern matching subdomains
        ("https://portal.myrealtor.com", ["myrealtor.com"], True),
        # Sanitization: pattern configured with protocol
        ("https://domain.com", ["https://domain.com/"], True),
        # Unauthorized origin
        ("https://hacker.com", ["agency.com", "localhost:3000"], False),
        # None or null origin
        (None, ["agency.com"], False),
        ("null", ["agency.com"], False),
    ],
)
def test_is_origin_allowed(origin: str | None, allowed_domains: list[str], expected: bool) -> None:
    assert is_origin_allowed(origin, allowed_domains) is expected


# ==============================================================================
# 3. Visitor JWT Token Lifecycle
# ==============================================================================


def test_create_and_decode_visitor_token_success() -> None:
    t_id = uuid.uuid4()
    v_id = uuid.uuid4()

    token = create_visitor_token(
        tenant_id=t_id,
        visitor_id=v_id,
        secret_key=SECRET_KEY,
        expires_delta=timedelta(hours=2),
    )

    claims = decode_visitor_token(token, SECRET_KEY)
    assert claims["sub"] == str(v_id)
    assert claims["tenant_id"] == str(t_id)
    assert claims["type"] == "visitor_session"
    assert claims["exp"] > claims["iat"]


def test_decode_visitor_token_expired() -> None:
    t_id = uuid.uuid4()
    v_id = uuid.uuid4()

    token = create_visitor_token(
        tenant_id=t_id,
        visitor_id=v_id,
        secret_key=SECRET_KEY,
        expires_delta=timedelta(seconds=-10),  # expired
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_visitor_token(token, SECRET_KEY)


def test_decode_visitor_token_invalid_signature() -> None:
    token = create_visitor_token(
        tenant_id=uuid.uuid4(),
        visitor_id=uuid.uuid4(),
        secret_key=SECRET_KEY,
    )

    with pytest.raises(jwt.InvalidSignatureError):
        decode_visitor_token(token, "wrong-secret-key")


# ==============================================================================
# 4. WidgetService
# ==============================================================================


def test_widget_service_create_new_session() -> None:
    tenant = make_tenant()
    service = WidgetService(secret_key=SECRET_KEY)

    session = service.create_or_resume_session(tenant=tenant)

    assert isinstance(session, WidgetSessionResponse)
    assert session.tenant_id == tenant.id
    assert session.tenant_name == tenant.name
    assert session.visitor_id is not None
    assert session.visitor_token is not None


def test_widget_service_resume_existing_visitor() -> None:
    tenant = make_tenant()
    existing_visitor_id = uuid.uuid4()
    service = WidgetService(secret_key=SECRET_KEY)

    session = service.create_or_resume_session(
        tenant=tenant, requested_visitor_id=existing_visitor_id
    )

    assert session.visitor_id == existing_visitor_id
    claims = decode_visitor_token(session.visitor_token, SECRET_KEY)
    assert claims["sub"] == str(existing_visitor_id)


# ==============================================================================
# 5. Widget Endpoints (HTTP Integration via ASGI)
# ==============================================================================


@pytest.fixture
def test_app() -> httpx.AsyncClient:
    app = create_app()
    tenant = make_tenant(
        widget_key="wk_live_test_key_123",
        allowed_domains=["allowed.com"],
    )

    # Mock settings secret_key
    app.dependency_overrides[get_settings] = lambda: Settings(
        secret_key=SecretStr(SECRET_KEY),
        database_url="postgresql+asyncpg://user:pass@localhost/db",
        redis_url="redis://localhost:6379",
        admin_api_key="adminkey",
    )

    # Mock get_widget_tenant dependency
    async def override_get_widget_tenant(request: Request) -> Tenant:
        key = request.headers.get("X-Widget-Key") or request.query_params.get("widget_key")
        if not key:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Missing widget key")
        if key != tenant.widget_key:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Invalid widget key")
        origin = request.headers.get("Origin")
        if not is_origin_allowed(origin, tenant.allowed_domains):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Unauthorized origin")
        return tenant

    # Mock get_current_visitor dependency
    async def override_get_current_visitor(request: Request) -> VisitorContext:
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Missing visitor token")
        token = auth.split(" ")[1]
        try:
            payload = decode_visitor_token(token, SECRET_KEY)
        except Exception as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Invalid token") from exc
        return VisitorContext(
            visitor_id=uuid.UUID(payload["sub"]),
            tenant_id=uuid.UUID(payload["tenant_id"]),
            tenant=tenant,
        )

    app.dependency_overrides[get_widget_tenant] = override_get_widget_tenant
    app.dependency_overrides[get_current_visitor] = override_get_current_visitor

    app.include_router(widget_router, prefix="/api/v1")
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_widget_session_endpoint_success(test_app: httpx.AsyncClient) -> None:
    response = await test_app.post(
        "/api/v1/widget/session",
        headers={
            "X-Widget-Key": "wk_live_test_key_123",
            "Origin": "https://allowed.com",
        },
        json={},
    )

    assert response.status_code == 200
    data = response.json()
    assert "visitor_token" in data
    assert "visitor_id" in data
    assert data["tenant_name"] == "Prime Properties"


@pytest.mark.asyncio
async def test_widget_session_missing_key(test_app: httpx.AsyncClient) -> None:
    response = await test_app.post(
        "/api/v1/widget/session",
        headers={"Origin": "https://allowed.com"},
        json={},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_widget_session_invalid_key(test_app: httpx.AsyncClient) -> None:
    response = await test_app.post(
        "/api/v1/widget/session",
        headers={
            "X-Widget-Key": "wk_live_wrong_key",
            "Origin": "https://allowed.com",
        },
        json={},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_widget_session_forbidden_origin(test_app: httpx.AsyncClient) -> None:
    response = await test_app.post(
        "/api/v1/widget/session",
        headers={
            "X-Widget-Key": "wk_live_test_key_123",
            "Origin": "https://unauthorized-domain.com",
        },
        json={},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_widget_session_resume_visitor(test_app: httpx.AsyncClient) -> None:
    existing_visitor = str(uuid.uuid4())
    response = await test_app.post(
        "/api/v1/widget/session",
        headers={
            "X-Widget-Key": "wk_live_test_key_123",
            "Origin": "https://allowed.com",
        },
        json={"visitor_id": existing_visitor},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["visitor_id"] == existing_visitor


@pytest.mark.asyncio
async def test_verify_widget_session_success(test_app: httpx.AsyncClient) -> None:
    # First get a valid token
    init_res = await test_app.post(
        "/api/v1/widget/session",
        headers={
            "X-Widget-Key": "wk_live_test_key_123",
            "Origin": "https://allowed.com",
        },
        json={},
    )
    token = init_res.json()["visitor_token"]

    # Verify session
    verify_res = await test_app.get(
        "/api/v1/widget/session/verify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["tenant_name"] == "Prime Properties"


@pytest.mark.asyncio
async def test_verify_widget_session_missing_token(test_app: httpx.AsyncClient) -> None:
    verify_res = await test_app.get("/api/v1/widget/session/verify")
    assert verify_res.status_code == 401
