class EmbeddingError(Exception):
    """Embedding provider failed and retries (if any) are exhausted."""


class EmbeddingDimensionError(EmbeddingError):
    """Provider returned vectors of an unexpected size."""