from types import SimpleNamespace
from typing import Any, Self, cast
from unittest.mock import AsyncMock, MagicMock

import httpx2
import openai
import pytest
from openai import AsyncOpenAI

from app.integrations.llm.base import ChatMessage
from app.integrations.llm.client import OpenRouterLLMClient
from app.integrations.llm.exceptions import (
    LLMBadResponseError,
    LLMError,
    LLMRateLimitError,
    LLMUnavailableError,
)

_REQUEST = httpx2.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
_MESSAGES = [
    ChatMessage(role="system", content="You are helpful."),
    ChatMessage(role="user", content="Hi"),
]


def _completion(content: str | None, *, with_usage: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        model="test-model",
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5) if with_usage else None,
    )


def _chunk(content: str | None, *, empty_choices: bool = False) -> SimpleNamespace:
    choices = [] if empty_choices else [SimpleNamespace(delta=SimpleNamespace(content=content))]
    return SimpleNamespace(choices=choices)


class _FakeStream:
    def __init__(self, chunks: list[SimpleNamespace]) -> None:
        self._chunks = chunks

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    def __aiter__(self) -> Any:
        return self._iterate()

    async def _iterate(self) -> Any:
        for chunk in self._chunks:
            yield chunk


def _make_client(create: AsyncMock) -> tuple[OpenRouterLLMClient, MagicMock]:
    sdk = MagicMock()
    sdk.chat.completions.create = create
    sdk.close = AsyncMock()
    client = OpenRouterLLMClient(
        client=cast(AsyncOpenAI, sdk),
        model="test-model",
        default_max_tokens=500,
        default_temperature=0.3,
    )
    return client, sdk


async def test_complete_returns_content_and_usage() -> None:
    client, sdk = _make_client(AsyncMock(return_value=_completion("Hello!")))

    result = await client.complete(_MESSAGES)

    assert result.content == "Hello!"
    assert result.model == "test-model"
    assert result.prompt_tokens == 10
    assert result.completion_tokens == 5
    kwargs = sdk.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "test-model"
    assert kwargs["max_tokens"] == 500
    assert kwargs["temperature"] == 0.3
    assert kwargs["messages"] == [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hi"},
    ]


async def test_complete_allows_per_call_overrides() -> None:
    client, sdk = _make_client(AsyncMock(return_value=_completion("ok")))

    await client.complete(_MESSAGES, max_tokens=100, temperature=0.0)

    kwargs = sdk.chat.completions.create.call_args.kwargs
    assert kwargs["max_tokens"] == 100
    assert kwargs["temperature"] == 0.0


async def test_complete_handles_missing_usage() -> None:
    client, _ = _make_client(AsyncMock(return_value=_completion("ok", with_usage=False)))

    result = await client.complete(_MESSAGES)

    assert result.prompt_tokens is None
    assert result.completion_tokens is None


@pytest.mark.parametrize("content", [None, ""])
async def test_complete_raises_on_empty_content(content: str | None) -> None:
    client, _ = _make_client(AsyncMock(return_value=_completion(content)))

    with pytest.raises(LLMBadResponseError):
        await client.complete(_MESSAGES)


async def test_complete_raises_on_no_choices() -> None:
    empty = SimpleNamespace(model="m", choices=[], usage=None)
    client, _ = _make_client(AsyncMock(return_value=empty))

    with pytest.raises(LLMBadResponseError):
        await client.complete(_MESSAGES)


@pytest.mark.parametrize(
    ("sdk_error", "expected"),
    [
        (
            openai.RateLimitError(
                "rate limited",
                response=httpx2.Response(429, request=_REQUEST),
                body=None,
            ),
            LLMRateLimitError,
        ),
        (openai.APIConnectionError(request=_REQUEST), LLMUnavailableError),
        (openai.APITimeoutError(request=_REQUEST), LLMUnavailableError),
        (
            openai.InternalServerError(
                "boom",
                response=httpx2.Response(500, request=_REQUEST),
                body=None,
            ),
            LLMUnavailableError,
        ),
        (
            openai.BadRequestError(
                "bad",
                response=httpx2.Response(400, request=_REQUEST),
                body=None,
            ),
            LLMError,
        ),
    ],
)
async def test_complete_translates_sdk_errors(
    sdk_error: openai.OpenAIError, expected: type[LLMError]
) -> None:
    client, _ = _make_client(AsyncMock(side_effect=sdk_error))

    with pytest.raises(expected):
        await client.complete(_MESSAGES)


async def test_stream_yields_only_non_empty_deltas() -> None:
    stream = _FakeStream(
        [
            _chunk(None, empty_choices=True),  # e.g. trailing usage chunk
            _chunk("Hel"),
            _chunk(None),  # role-only / finish chunk
            _chunk(""),
            _chunk("lo"),
        ]
    )
    client, sdk = _make_client(AsyncMock(return_value=stream))

    tokens = [token async for token in client.stream(_MESSAGES)]

    assert tokens == ["Hel", "lo"]
    assert sdk.chat.completions.create.call_args.kwargs["stream"] is True


async def test_stream_translates_sdk_errors() -> None:
    client, _ = _make_client(
        AsyncMock(side_effect=openai.APIConnectionError(request=_REQUEST))
    )

    with pytest.raises(LLMUnavailableError):
        async for _ in client.stream(_MESSAGES):
            pass


async def test_close_closes_underlying_sdk_client() -> None:
    client, sdk = _make_client(AsyncMock())

    await client.close()

    sdk.close.assert_awaited_once()