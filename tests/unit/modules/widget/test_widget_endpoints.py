"""Unit tests for public widget visitor-isolated conversation and SSE streaming endpoints."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
import uuid
from unittest.mock import AsyncMock, create_autospec

import httpx
from pydantic import SecretStr
import pytest
from starlette.requests import Request

from app.core.config import Settings
from app.core.security import create_visitor_token
from app.main import create_app
from app.modules.chat.dependencies import get_chat_service
from app.modules.chat.enums import MessageRole
from app.modules.chat.exceptions import ConversationNotFoundError
from app.modules.chat.models import Conversation, Message
from app.modules.chat.service import ChatService
from app.modules.tenants.models import Tenant
from app.modules.widget.dependencies import (
    VisitorContext,
    get_current_visitor,
    get_widget_tenant,
)
from app.modules.widget.router import router as widget_router

SECRET_KEY = "test-secret-key-for-visitor-endpoint-tests"
TENANT_ID = uuid.uuid4()
VISITOR_A_ID = uuid.uuid4()
VISITOR_B_ID = uuid.uuid4()
NOW = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)


def make_tenant() -> Tenant:
    t = Tenant()
    t.id = TENANT_ID
    t.name = "Prestige Realty"
    t.slug = "prestige-realty"
    t.api_key_hash = "hash123"
    t.api_key_prefix = "rk_live_12"
    t.widget_key = "wk_live_valid123"
    t.allowed_domains = ["*"]
    t.is_active = True
    t.created_at = NOW
    t.updated_at = NOW
    return t


def make_conversation(**overrides: Any) -> Conversation:
    values: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": TENANT_ID,
        "title": "Property Inquiry",
        "metadata_": {"visitor_id": str(VISITOR_A_ID), "source": "embed_widget"},
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    meta = values.get("metadata_", values.get("metadata", {}))
    conv = Conversation(
        tenant_id=values["tenant_id"],
        title=values["title"],
        metadata_=meta,
    )
    conv.id = values["id"]
    conv.created_at = values["created_at"]
    conv.updated_at = values["updated_at"]
    return conv


def make_message(**overrides: Any) -> Message:
    values: dict[str, Any] = {
        "id": uuid.uuid4(),
        "conversation_id": uuid.uuid4(),
        "tenant_id": TENANT_ID,
        "role": MessageRole.ASSISTANT,
        "content": "Prices start at $1,200,000.",
        "token_count": 10,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    msg = Message(**values)
    msg.id = values["id"]
    msg.created_at = values["created_at"]
    msg.updated_at = values["updated_at"]
    return msg


@pytest.fixture
def mock_chat_service() -> AsyncMock:
    service = create_autospec(ChatService, instance=True)
    return service


@pytest.fixture
def test_app(mock_chat_service: AsyncMock) -> httpx.AsyncClient:
    app = create_app()
    tenant = make_tenant()

    app.dependency_overrides[Settings] = lambda: Settings(
        secret_key=SecretStr(SECRET_KEY),
        database_url="postgresql+asyncpg://user:pass@localhost/db",
        redis_url="redis://localhost:6379",
        admin_api_key="adminkey",
    )

    app.dependency_overrides[get_chat_service] = lambda: mock_chat_service

    # Provide visitor dependency override inspecting Bearer token
    async def override_get_current_visitor(request: Request) -> VisitorContext:
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Missing visitor token")
        token = auth.split(" ")[1]
        if token == "token_visitor_a":
            return VisitorContext(visitor_id=VISITOR_A_ID, tenant_id=TENANT_ID, tenant=tenant)
        elif token == "token_visitor_b":
            return VisitorContext(visitor_id=VISITOR_B_ID, tenant_id=TENANT_ID, tenant=tenant)
        else:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Invalid token")

    app.dependency_overrides[get_current_visitor] = override_get_current_visitor

    app.include_router(widget_router, prefix="/api/v1")
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


# ==============================================================================
# Visitor-Isolated Conversation Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_create_widget_conversation(
    test_app: httpx.AsyncClient, mock_chat_service: AsyncMock
) -> None:
    expected_conv = make_conversation()
    mock_chat_service.create_conversation.return_value = expected_conv

    response = await test_app.post(
        "/api/v1/widget/conversations",
        headers={"Authorization": "Bearer token_visitor_a"},
        json={"title": "Penthouse Inquiry"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(expected_conv.id)
    assert data["title"] == expected_conv.title

    mock_chat_service.create_conversation.assert_awaited_once()
    kwargs = mock_chat_service.create_conversation.call_args.kwargs
    assert kwargs["tenant_id"] == TENANT_ID
    assert kwargs["metadata"]["visitor_id"] == str(VISITOR_A_ID)


@pytest.mark.asyncio
async def test_list_widget_conversations_isolated(
    test_app: httpx.AsyncClient, mock_chat_service: AsyncMock
) -> None:
    conv_a = make_conversation(title="Visitor A Chat")
    mock_chat_service.list_conversations_for_visitor.return_value = [conv_a]

    response = await test_app.get(
        "/api/v1/widget/conversations",
        headers={"Authorization": "Bearer token_visitor_a"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Visitor A Chat"
    mock_chat_service.list_conversations_for_visitor.assert_awaited_once_with(
        tenant_id=TENANT_ID,
        visitor_id=str(VISITOR_A_ID),
        limit=20,
        offset=0,
    )


@pytest.mark.asyncio
async def test_get_widget_conversation_not_found_or_unowned(
    test_app: httpx.AsyncClient, mock_chat_service: AsyncMock
) -> None:
    conv_id = uuid.uuid4()
    mock_chat_service.get_conversation_for_visitor.side_effect = ConversationNotFoundError("Not found")

    response = await test_app.get(
        f"/api/v1/widget/conversations/{conv_id}",
        headers={"Authorization": "Bearer token_visitor_b"},
    )

    assert response.status_code == 404
    mock_chat_service.get_conversation_for_visitor.assert_awaited_once_with(
        tenant_id=TENANT_ID,
        conversation_id=conv_id,
        visitor_id=str(VISITOR_B_ID),
    )


@pytest.mark.asyncio
async def test_send_widget_message_success(
    test_app: httpx.AsyncClient, mock_chat_service: AsyncMock
) -> None:
    conv = make_conversation()
    reply = make_message(content="The waterfront villa is available.")
    mock_chat_service.get_conversation_for_visitor.return_value = conv
    mock_chat_service.send_message.return_value = reply

    response = await test_app.post(
        f"/api/v1/widget/conversations/{conv.id}/messages",
        headers={"Authorization": "Bearer token_visitor_a"},
        json={"content": "Is the waterfront villa still available?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "The waterfront villa is available."


@pytest.mark.asyncio
async def test_stream_widget_chat_success(
    test_app: httpx.AsyncClient, mock_chat_service: AsyncMock
) -> None:
    conv = make_conversation()
    mock_chat_service.get_conversation_for_visitor.return_value = conv

    async def fake_tokens(*args: Any, **kwargs: Any) -> AsyncIterator[str]:
        for token in ["Hello", " world", "!"]:
            yield token

    mock_chat_service.stream_chat.return_value = fake_tokens()

    response = await test_app.post(
        f"/api/v1/widget/conversations/{conv.id}/stream",
        headers={"Authorization": "Bearer token_visitor_a"},
        json={"content": "Tell me about prices"},
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    content = response.text
    assert 'data: {"token": "Hello"}' in content
    assert 'data: {"token": " world"}' in content
    assert 'data: {"token": "!"}' in content
    assert "data: [DONE]" in content
