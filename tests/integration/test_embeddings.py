import asyncio
from collections.abc import AsyncIterator

import pytest

from app.core.config import get_settings
from app.integrations.embeddings.client import EmbeddingClient

settings = get_settings()
_key = settings.openrouter_api_key.get_secret_value()
_has_live_key = bool(_key and not _key.startswith("mock") and not _key.startswith("change_me"))


@pytest.fixture
async def embedding_client() -> AsyncIterator[EmbeddingClient]:
    client = EmbeddingClient()
    try:
        yield client
    finally:
        await client.aclose()


@pytest.mark.integration
@pytest.mark.skipif(not _has_live_key, reason="Live OpenRouter API key is not configured")
async def test_live_embed_documents(embedding_client: EmbeddingClient) -> None:
    texts = [
        "2 bedroom apartment in Dubai Marina",
        "villa with private pool",
    ]
    vectors = await embedding_client.embed_documents(texts)
    assert len(vectors) == 2
    assert len(vectors[0]) == settings.embedding_dimension
    assert len(vectors[1]) == settings.embedding_dimension


@pytest.mark.integration
@pytest.mark.skipif(not _has_live_key, reason="Live OpenRouter API key is not configured")
async def test_live_embed_query(embedding_client: EmbeddingClient) -> None:
    vector = await embedding_client.embed_query("luxury beachfront penthouse")
    assert isinstance(vector, list)
    assert len(vector) == settings.embedding_dimension


async def _run_manual() -> None:
    client = EmbeddingClient()
    try:
        texts = [
            "2 bedroom apartment in Dubai Marina",
            "villa with private pool",
        ]
        vectors = await client.embed_documents(texts)
        print(f"Success! Generated {len(vectors)} embeddings.")
        print(f"Dimension of first vector: {len(vectors[0])}")
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(_run_manual())
