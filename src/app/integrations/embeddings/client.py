import asyncio
import logging
import random
from collections.abc import Sequence

import httpx

from app.core.config import get_settings
from app.integrations.embeddings.exceptions import EmbeddingDimensionError, EmbeddingError

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}
_BACKOFF_BASE_SECONDS = 1.0
_BACKOFF_MAX_SECONDS = 30.0


class EmbeddingClient:
    """Async OpenRouter embeddings client with batching, bounded concurrency and retries."""

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        settings = get_settings()
        self._model = settings.embedding_model
        self._dimension = settings.embedding_dimension
        self._batch_size = settings.embedding_batch_size
        self._max_retries = settings.embedding_max_retries
        self._semaphore = asyncio.Semaphore(settings.embedding_max_concurrency)
        self._http = http_client or httpx.AsyncClient(
            base_url=settings.openrouter_base_url,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(settings.embedding_timeout_seconds, connect=10.0),
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed many texts. Output order always matches input order."""
        if not texts:
            return []
        if any(not t or not t.strip() for t in texts):
            raise ValueError("Cannot embed empty text.")

        batches = [
            list(texts[i : i + self._batch_size])
            for i in range(0, len(texts), self._batch_size)
        ]
        results = await asyncio.gather(*(self._embed_batch(b) for b in batches))
        return [vector for batch in results for vector in batch]

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed_documents([text]))[0]

    async def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        async with self._semaphore:
            body = await self._post_with_retry({"model": self._model, "input": batch})

        data = body["data"]
        if len(data) != len(batch):
            raise EmbeddingError(
                f"Provider returned {len(data)} embeddings for {len(batch)} inputs."
            )

        vectors = [item["embedding"] for item in sorted(data, key=lambda d: d["index"])]
        for vector in vectors:
            if len(vector) != self._dimension:
                raise EmbeddingDimensionError(
                    f"Expected {self._dimension}-dim vectors, got {len(vector)}. "
                    "Check EMBEDDING_MODEL / EMBEDDING_DIMENSION."
                )
        return vectors

    async def _post_with_retry(self, payload: dict) -> dict:
        last_error = "unknown error"

        for attempt in range(1, self._max_retries + 1):
            retry_after: float | None = None
            try:
                response = await self._http.post("/embeddings", json=payload)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code == 200:
                    body = response.json()
                    # OpenRouter can return HTTP 200 with an error object in the body
                    if "data" in body:
                        return body
                    last_error = f"Error in 200 response: {body.get('error')}"
                elif response.status_code in _RETRYABLE_STATUS:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    retry_after = self._parse_retry_after(response)
                else:
                    # 400/401/402/403/404 etc: retrying will not help
                    raise EmbeddingError(
                        f"Embedding request rejected (HTTP {response.status_code}): "
                        f"{response.text[:300]}"
                    )

            if attempt == self._max_retries:
                break

            delay = retry_after if retry_after is not None else self._backoff(attempt)
            logger.warning(
                "Embedding request failed (attempt %s/%s): %s. Retrying in %.1fs",
                attempt, self._max_retries, last_error, delay,
            )
            await asyncio.sleep(delay)

        raise EmbeddingError(
            f"Embedding request failed after {self._max_retries} attempts: {last_error}"
        )

    @staticmethod
    def _backoff(attempt: int) -> float:
        # Exponential backoff with full jitter
        return random.uniform(0, min(_BACKOFF_MAX_SECONDS, _BACKOFF_BASE_SECONDS * 2**attempt))

    @staticmethod
    def _parse_retry_after(response: httpx.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if value is None:
            return None
        try:
            return min(float(value), _BACKOFF_MAX_SECONDS)
        except ValueError:
            return None


_client: EmbeddingClient | None = None


def init_embedding_client() -> EmbeddingClient:
    global _client
    if _client is None:
        _client = EmbeddingClient()
    return _client


def get_embedding_client() -> EmbeddingClient:
    if _client is None:
        raise RuntimeError("Embedding client is not initialised. Call init_embedding_client().")
    return _client


async def close_embedding_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None