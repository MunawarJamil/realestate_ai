from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol defining the contract for embedding providers."""

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed multiple text strings in batch. Order is preserved."""
        ...

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query string for semantic retrieval."""
        ...

    async def aclose(self) -> None:
        """Release underlying HTTP and network resources."""
        ...
