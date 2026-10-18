import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.chat.enums import MessageRole
from app.modules.chat.models import Conversation, Message
from app.modules.chat.repository import ChatRepository


@pytest.fixture
def mock_session() -> MagicMock:
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session: MagicMock) -> ChatRepository:
    return ChatRepository(mock_session)


async def test_create_conversation(repo: ChatRepository, mock_session: MagicMock) -> None:
    tenant_id = uuid.uuid4()
    conv = await repo.create_conversation(
        tenant_id=tenant_id,
        title="Test Chat",
        metadata={"source": "api"},
    )

    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()
    assert conv.tenant_id == tenant_id
    assert conv.title == "Test Chat"
    assert conv.metadata_ == {"source": "api"}


async def test_get_conversation(repo: ChatRepository, mock_session: MagicMock) -> None:
    tenant_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    fake_conv = Conversation(tenant_id=tenant_id, title="Test")

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = fake_conv
    mock_session.execute.return_value = exec_result

    found = await repo.get_conversation(tenant_id=tenant_id, conversation_id=conv_id)
    assert found == fake_conv


async def test_create_and_list_messages(repo: ChatRepository, mock_session: MagicMock) -> None:
    tenant_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    msg = await repo.create_message(
        tenant_id=tenant_id,
        conversation_id=conv_id,
        role=MessageRole.USER,
        content="What is the price?",
    )

    mock_session.add.assert_called_once()
    assert msg.role == MessageRole.USER
    assert msg.content == "What is the price?"

    exec_result = MagicMock()
    exec_result.scalars.return_value.all.return_value = [msg]
    mock_session.execute.return_value = exec_result

    messages = await repo.list_messages(tenant_id=tenant_id, conversation_id=conv_id)
    assert len(messages) == 1
    assert messages[0] == msg


async def test_get_recent_messages_order(repo: ChatRepository, mock_session: MagicMock) -> None:
    tenant_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    m1 = Message(tenant_id=tenant_id, conversation_id=conv_id, role=MessageRole.USER, content="1")
    m2 = Message(
        tenant_id=tenant_id, conversation_id=conv_id, role=MessageRole.ASSISTANT, content="2"
    )

    # DB returns desc (latest first: [m2, m1])
    exec_result = MagicMock()
    exec_result.scalars.return_value.all.return_value = [m2, m1]
    mock_session.execute.return_value = exec_result

    # Repository returns reversed (chronological: [m1, m2])
    recent = await repo.get_recent_messages(tenant_id=tenant_id, conversation_id=conv_id, limit=2)
    assert recent == [m1, m2]
