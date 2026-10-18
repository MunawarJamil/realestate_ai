import logging
from collections.abc import AsyncIterator, Sequence
from typing import cast

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.core.config import Settings
from app.integrations.llm.base import ChatMessage, LLMResponse
from app.integrations.llm.exceptions import (
    LLMBadResponseError,
    LLMError,
    LLMRateLimitError,
    LLMUnavailableError,
)

logger = logging.getLogger(__name__)


def _to_params(messages: Sequence[ChatMessage]) -> list[ChatCompletionMessageParam]:
    return cast(
        "list[ChatCompletionMessageParam]",
        [{"role": m.role, "content": m.content} for m in messages],
    )


def _translate(exc: openai.OpenAIError) -> LLMError:
    # Never log message content here: it may contain customer PII.
    if isinstance(exc, openai.RateLimitError):
        logger.warning("llm_rate_limited")
        return LLMRateLimitError("LLM provider rate limit reached")
    if isinstance(exc, (openai.APIConnectionError, openai.InternalServerError)):
        logger.warning("llm_unavailable", extra={"error_type": type(exc).__name__})
        return LLMUnavailableError("LLM provider unavailable")
    logger.error("llm_request_failed", extra={"error_type": type(exc).__name__})
    return LLMError("LLM request failed")


class OpenRouterLLMClient:
    """LLMProvider backed by the OpenAI SDK pointed at OpenRouter.

    Retries on connection errors, 408/409/429 and 5xx are handled by the SDK
    (max_retries), so we do not add our own retry loop on top.
    """

    def __init__(
        self,
        *,
        client: AsyncOpenAI,
        model: str,
        default_max_tokens: int,
        default_temperature: float,
    ) -> None:
        self._client = client
        self._model = model
        self._default_max_tokens = default_max_tokens
        self._default_temperature = default_temperature

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=_to_params(messages),
                max_tokens=max_tokens or self._default_max_tokens,
                temperature=self._default_temperature if temperature is None else temperature,
            )
        except openai.OpenAIError as exc:
            raise _translate(exc) from exc

        # Free models occasionally return empty choices / null content.
        if not response.choices or not response.choices[0].message.content:
            raise LLMBadResponseError("LLM returned an empty completion")

        usage = response.usage
        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model or self._model,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
        )

    async def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=_to_params(messages),
                max_tokens=max_tokens or self._default_max_tokens,
                temperature=self._default_temperature if temperature is None else temperature,
                stream=True,
            )
            # `async with` releases the HTTP connection even if the consumer
            # stops early (e.g. client disconnects from SSE).
            async with response:
                async for chunk in response:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
        except openai.OpenAIError as exc:
            raise _translate(exc) from exc

    async def close(self) -> None:
        await self._client.close()


def build_llm_client(settings: Settings) -> OpenRouterLLMClient:
    api_key = settings.openrouter_api_key.get_secret_value() or "not-configured"
    sdk = AsyncOpenAI(
        api_key=api_key,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )
    return OpenRouterLLMClient(
        client=sdk,
        model=settings.llm_model,
        default_max_tokens=settings.llm_max_tokens,
        default_temperature=settings.llm_temperature,
    )