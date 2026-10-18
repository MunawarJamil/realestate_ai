import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.integrations.llm.base import ChatMessage, LLMProvider, LLMResponse
from app.integrations.llm.exceptions import LLMError
from app.modules.chat.enums import MessageRole
from app.modules.chat.exceptions import (
    ChatServiceUnavailableError,
    ConversationNotFoundError,
    InvalidMessageError,
)
from app.modules.chat.models import Conversation, Message
from app.modules.chat.repository import ChatRepository
from app.modules.chat.service import ChatService
from app.modules.knowledge.retrieval import RetrievalService, RetrievedChunk


@pytest.fixture
def mock_repo() -> MagicMock:
    repo = MagicMock(spec=ChatRepository)
    repo.create_conversation = AsyncMock()
    repo.get_conversation = AsyncMock()
    repo.list_conversations = AsyncMock()
    repo.list_messages = AsyncMock()
    repo.create_message = AsyncMock()
    repo.get_recent_messages = AsyncMock()
    return repo


@pytest.fixture
def mock_retrieval() -> MagicMock:
    retrieval = MagicMock(spec=RetrievalService)
    retrieval.search = AsyncMock()
    return retrieval


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock(spec=LLMProvider)
    llm.complete = AsyncMock()
    llm.stream = MagicMock()
    return llm


@pytest.fixture
def service(
    mock_repo: MagicMock,
    mock_retrieval: MagicMock,
    mock_llm: MagicMock,
) -> ChatService:
    return ChatService(
        repository=mock_repo,
        retrieval=mock_retrieval,
        llm=mock_llm,
    )


async def test_get_conversation_not_found_raises(
    service: ChatService, mock_repo: MagicMock
) -> None:
    mock_repo.get_conversation.return_value = None
    with pytest.raises(ConversationNotFoundError):
        await service.get_conversation(tenant_id=uuid.uuid4(), conversation_id=uuid.uuid4())


async def test_send_message_empty_content_raises(service: ChatService) -> None:
    with pytest.raises(InvalidMessageError):
        await service.send_message(
            tenant_id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            user_message="   ",
        )


async def test_send_message_success(
    service: ChatService,
    mock_repo: MagicMock,
    mock_retrieval: MagicMock,
    mock_llm: MagicMock,
) -> None:
    tenant_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    conv = Conversation(tenant_id=tenant_id, title="Test")
    mock_repo.get_conversation.return_value = conv

    user_msg = Message(
        tenant_id=tenant_id,
        conversation_id=conv_id,
        role=MessageRole.USER,
        content="What is the price?",
    )
    mock_repo.get_recent_messages.return_value = [user_msg]

    mock_retrieval.search.return_value = [
        RetrievedChunk(
            document_id=uuid.uuid4(),
            document_title="Pricing.pdf",
            page_number=1,
            chunk_index=0,
            text="Price is $500,000",
            score=0.9,
        )
    ]

    mock_llm.complete.return_value = LLMResponse(
        content="The unit is priced at $500,000.",
        model="test-model",
        completion_tokens=15,
    )

    assistant_msg = Message(
        tenant_id=tenant_id,
        conversation_id=conv_id,
        role=MessageRole.ASSISTANT,
        content="The unit is priced at $500,000.",
        token_count=15,
    )
    mock_repo.create_message.return_value = assistant_msg

    result = await service.send_message(
        tenant_id=tenant_id,
        conversation_id=conv_id,
        user_message="What is the price?",
    )

    assert result == assistant_msg
    # Verify user message saved
    assert mock_repo.create_message.call_count == 2
    mock_retrieval.search.assert_awaited_once_with(tenant_id=tenant_id, query="What is the price?")
    mock_llm.complete.assert_awaited_once()


async def test_stream_chat_success(
    service: ChatService,
    mock_repo: MagicMock,
    mock_retrieval: MagicMock,
    mock_llm: MagicMock,
) -> None:
    tenant_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    conv = Conversation(tenant_id=tenant_id, title="Stream Test")
    mock_repo.get_conversation.return_value = conv

    user_msg = Message(
        tenant_id=tenant_id,
        conversation_id=conv_id,
        role=MessageRole.USER,
        content="Hello",
    )
    mock_repo.get_recent_messages.return_value = [user_msg]
    mock_retrieval.search.return_value = []

    async def fake_stream(_messages: list[ChatMessage]) -> AsyncIterator[str]:
        for token in ["Hello", " there", "!"]:
            yield token

    mock_llm.stream.return_value = fake_stream([])

    tokens = [
        t
        async for t in service.stream_chat(
            tenant_id=tenant_id,
            conversation_id=conv_id,
            user_message="Hello",
        )
    ]

    assert tokens == ["Hello", " there", "!"]
    # Check that assistant message was saved with full content
    mock_repo.create_message.assert_called_with(
        tenant_id=tenant_id,
        conversation_id=conv_id,
        role=MessageRole.ASSISTANT,
        content="Hello there!",
    )


async def test_stream_chat_llm_error_translates(
    service: ChatService,
    mock_repo: MagicMock,
    mock_llm: MagicMock,
) -> None:
    tenant_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    mock_repo.get_conversation.return_value = Conversation(tenant_id=tenant_id)
    mock_repo.get_recent_messages.return_value = []

    async def error_stream(_messages: list[ChatMessage]) -> AsyncIterator[str]:
        raise LLMError("Provider down")
        yield "never"

    mock_llm.stream.return_value = error_stream([])

    with pytest.raises(ChatServiceUnavailableError):
        _ = [
            t
            async for t in service.stream_chat(
                tenant_id=tenant_id,
                conversation_id=conv_id,
                user_message="Hi",
            )
        ]
