from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
import uuid
from unittest.mock import AsyncMock, create_autospec

import httpx
import pytest
from fastapi import FastAPI

from app.modules.chat.dependencies import get_chat_service
from app.modules.chat.enums import MessageRole
from app.modules.chat.exceptions import ConversationNotFoundError, InvalidMessageError
from app.modules.chat.models import Conversation, Message
from app.modules.chat.router import router
from app.modules.chat.service import ChatService
from app.modules.tenants.dependencies import get_current_tenant

TENANT = SimpleNamespace(id=uuid.uuid4())
NOW = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)

def make_conversation(**overrides: Any) -> Conversation:
    values: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": TENANT.id,
        "title": "Apartment Inquiry",
        "metadata_": {"source": "web"},
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
        "tenant_id": TENANT.id,
        "role": MessageRole.ASSISTANT,
        "content": "Prices start at $300,000.",
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
def service() -> ChatService:
    mock: ChatService = create_autospec(ChatService, instance=True)
    return mock


@pytest.fixture
async def client(service: ChatService) -> AsyncIterator[httpx.AsyncClient]:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_tenant] = lambda: TENANT
    app.dependency_overrides[get_chat_service] = lambda: service

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as http_client:
        yield http_client


async def test_create_conversation_endpoint(
    client: httpx.AsyncClient, service: ChatService
) -> None:
    conv = make_conversation()
    service.create_conversation = AsyncMock(return_value=conv)

    response = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Apartment Inquiry", "metadata": {"source": "web"}},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == str(conv.id)
    assert body["title"] == "Apartment Inquiry"
    assert body["metadata"] == {"source": "web"}


async def test_list_conversations_endpoint(
    client: httpx.AsyncClient, service: ChatService
) -> None:
    conv = make_conversation()
    service.list_conversations = AsyncMock(return_value=[conv])

    response = await client.get("/api/v1/chat/conversations")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == str(conv.id)


async def test_get_conversation_found(
    client: httpx.AsyncClient, service: ChatService
) -> None:
    conv = make_conversation()
    service.get_conversation = AsyncMock(return_value=conv)

    response = await client.get(f"/api/v1/chat/conversations/{conv.id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(conv.id)


async def test_get_conversation_not_found(
    client: httpx.AsyncClient, service: ChatService
) -> None:
    fake_id = uuid.uuid4()
    service.get_conversation = AsyncMock(
        side_effect=ConversationNotFoundError("Not found")
    )

    response = await client.get(f"/api/v1/chat/conversations/{fake_id}")
    assert response.status_code == 404
    assert "Not found" in response.json()["detail"]


async def test_list_messages_endpoint(
    client: httpx.AsyncClient, service: ChatService
) -> None:
    conv_id = uuid.uuid4()
    msg = make_message(conversation_id=conv_id)
    service.list_messages = AsyncMock(return_value=[msg])

    response = await client.get(f"/api/v1/chat/conversations/{conv_id}/messages")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(msg.id)
    assert body[0]["content"] == "Prices start at $300,000."


async def test_send_message_endpoint_success(
    client: httpx.AsyncClient, service: ChatService
) -> None:
    conv_id = uuid.uuid4()
    msg = make_message(conversation_id=conv_id)
    service.send_message = AsyncMock(return_value=msg)

    response = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"content": "What is the price?"},
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Prices start at $300,000."


async def test_stream_chat_endpoint_success(
    client: httpx.AsyncClient, service: ChatService
) -> None:
    conv_id = uuid.uuid4()
    service.get_conversation = AsyncMock(return_value=make_conversation(id=conv_id))

    async def fake_stream(**_kwargs: Any) -> AsyncIterator[str]:
        yield "Hello"
        yield " client"

    service.stream_chat = fake_stream  # type: ignore[assignment]

    response = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/stream",
        json={"content": "Hi there"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    text = response.text
    assert 'data: {"token": "Hello"}' in text
    assert 'data: {"token": " client"}' in text
    assert "data: [DONE]" in text


async def test_stream_chat_not_found_returns_404(
    client: httpx.AsyncClient, service: ChatService
) -> None:
    fake_id = uuid.uuid4()
    service.get_conversation = AsyncMock(
        side_effect=ConversationNotFoundError("Not found")
    )

    response = await client.post(
        f"/api/v1/chat/conversations/{fake_id}/stream",
        json={"content": "Hi there"},
    )
    assert response.status_code == 404
