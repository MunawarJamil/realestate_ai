from app.core.config import get_settings
from qdrant_client import AsyncQdrantClient


_client: AsyncQdrantClient | None = None


def init_qdrant() -> AsyncQdrantClient:
    """Create the process-wide Qdrant client. Called once at app startup."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=settings.qdrant_timeout_seconds,
            check_compatibility=False,
        )
    return _client


def get_qdrant() -> AsyncQdrantClient:
    if _client is None:
        raise RuntimeError("Qdrant client is not initialised. Call init_qdrant() at startup.")
    return _client


async def close_qdrant() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None