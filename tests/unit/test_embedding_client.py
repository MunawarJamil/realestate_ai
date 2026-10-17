import json
from collections.abc import AsyncIterator, Callable
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr

from app.integrations.embeddings import client as client_module
from app.integrations.embeddings.client import EmbeddingClient
from app.integrations.embeddings.exceptions import EmbeddingDimensionError, EmbeddingError

DIM = 4
MAX_RETRIES = 3

Step = Callable[[httpx.Request], httpx.Response]


def _inputs(request: httpx.Request) -> list[str]:
    inputs: list[str] = json.loads(request.content)["input"]
    return inputs


def ok(*, dim: int = DIM, shuffle: bool = False, drop_last: bool = False) -> Step:
    """Successful response. Vector value == len(text), so order is verifiable."""

    def step(request: httpx.Request) -> httpx.Response:
        texts = _inputs(request)
        data = [{"index": i, "embedding": [float(len(t))] * dim} for i, t in enumerate(texts)]
        if drop_last:
            data = data[:-1]
        if shuffle:
            data.reverse()
        return httpx.Response(200, json={"data": data})

    return step


def status(code: int, headers: dict[str, str] | None = None) -> Step:
    return lambda request: httpx.Response(code, text="error", headers=headers)


def body_error() -> Step:
    return lambda request: httpx.Response(200, json={"error": {"message": "upstream failed"}})


def network_error() -> Step:
    def step(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    return step


class Script:
    """Plays steps in order; the last step repeats. Records every request."""

    def __init__(self, *steps: Step) -> None:
        self._steps = list(steps)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        step = self._steps.pop(0) if len(self._steps) > 1 else self._steps[0]
        return step(request)


ClientFactory = Callable[[Script], EmbeddingClient]


@pytest.fixture(autouse=True)
def stub_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        embedding_model="test-model",
        embedding_dimension=DIM,
        embedding_batch_size=2,
        embedding_max_retries=MAX_RETRIES,
        embedding_max_concurrency=2,
        openrouter_api_key=SecretStr("test-key"),
        openrouter_base_url="https://openrouter.test",
        embedding_timeout_seconds=5.0,
    )
    monkeypatch.setattr(client_module, "get_settings", lambda: settings)
    # No real waiting between retries
    monkeypatch.setattr(EmbeddingClient, "_backoff", staticmethod(lambda attempt: 0.0))


@pytest.fixture
async def build_client() -> AsyncIterator[ClientFactory]:
    created: list[EmbeddingClient] = []

    def _build(script: Script) -> EmbeddingClient:
        http = httpx.AsyncClient(
            base_url="https://openrouter.test",
            transport=httpx.MockTransport(script),
        )
        client = EmbeddingClient(http_client=http)
        created.append(client)
        return client

    yield _build

    for client in created:
        await client.aclose()


async def test_empty_input_returns_empty_without_calling_provider(
    build_client: ClientFactory,
) -> None:
    script = Script(ok())
    client = build_client(script)

    assert await client.embed_documents([]) == []
    assert script.requests == []


@pytest.mark.parametrize("bad_text", ["", "   ", "\n\t"])
async def test_blank_text_is_rejected(build_client: ClientFactory, bad_text: str) -> None:
    client = build_client(Script(ok()))

    with pytest.raises(ValueError):
        await client.embed_documents(["valid", bad_text])


async def test_order_is_preserved_across_batches_and_shuffled_responses(
    build_client: ClientFactory,
) -> None:
    script = Script(ok(shuffle=True))
    client = build_client(script)
    texts = ["a" * n for n in range(1, 6)]  # 5 texts, batch size 2 -> 3 requests

    vectors = await client.embed_documents(texts)

    assert len(script.requests) == 3
    assert vectors == [[float(n)] * DIM for n in range(1, 6)]


async def test_request_payload_contains_model_and_inputs(build_client: ClientFactory) -> None:
    script = Script(ok())
    client = build_client(script)

    await client.embed_documents(["hello"])

    payload = json.loads(script.requests[0].content)
    assert payload == {"model": "test-model", "input": ["hello"]}
    assert script.requests[0].url.path == "/embeddings"


async def test_embed_query_returns_single_vector(build_client: ClientFactory) -> None:
    client = build_client(Script(ok()))

    assert await client.embed_query("abc") == [3.0] * DIM


@pytest.mark.parametrize("code", [429, 500, 503])
async def test_retryable_status_is_retried_then_succeeds(
    build_client: ClientFactory, code: int
) -> None:
    script = Script(status(code, {"Retry-After": "0"}), ok())
    client = build_client(script)

    vectors = await client.embed_documents(["abc"])

    assert vectors == [[3.0] * DIM]
    assert len(script.requests) == 2


async def test_network_error_is_retried(build_client: ClientFactory) -> None:
    script = Script(network_error(), ok())
    client = build_client(script)

    assert await client.embed_documents(["abc"]) == [[3.0] * DIM]
    assert len(script.requests) == 2


async def test_error_inside_200_response_is_retried(build_client: ClientFactory) -> None:
    script = Script(body_error(), ok())
    client = build_client(script)

    assert await client.embed_documents(["abc"]) == [[3.0] * DIM]
    assert len(script.requests) == 2


@pytest.mark.parametrize("code", [400, 401, 402, 404])
async def test_non_retryable_status_fails_immediately(
    build_client: ClientFactory, code: int
) -> None:
    script = Script(status(code))
    client = build_client(script)

    with pytest.raises(EmbeddingError, match=str(code)):
        await client.embed_documents(["abc"])

    assert len(script.requests) == 1


async def test_raises_after_max_retries_exhausted(build_client: ClientFactory) -> None:
    script = Script(status(503))
    client = build_client(script)

    with pytest.raises(EmbeddingError, match=f"{MAX_RETRIES} attempts"):
        await client.embed_documents(["abc"])

    assert len(script.requests) == MAX_RETRIES


async def test_dimension_mismatch_raises(build_client: ClientFactory) -> None:
    client = build_client(Script(ok(dim=DIM + 1)))

    with pytest.raises(EmbeddingDimensionError):
        await client.embed_documents(["abc"])


async def test_embedding_count_mismatch_raises(build_client: ClientFactory) -> None:
    client = build_client(Script(ok(drop_last=True)))

    with pytest.raises(EmbeddingError, match="embeddings for"):
        await client.embed_documents(["a", "bb"])