import logging

from qdrant_client import AsyncQdrantClient, models

from app.core.config import get_settings

logger = logging.getLogger(__name__)

TENANT_FIELD = "tenant_id"
DOCUMENT_FIELD = "document_id"


async def ensure_collection(client: AsyncQdrantClient) -> None:
    """Create the shared multi-tenant collection if missing; fail fast on config drift."""
    settings = get_settings()
    name = settings.qdrant_collection

    if await client.collection_exists(name):
        await _validate_collection(client, name)
        logger.info("Qdrant collection '%s' already exists", name)
        return

    await client.create_collection(
        collection_name=name,
        vectors_config=models.VectorParams(
            size=settings.embedding_dimension,
            distance=models.Distance.COSINE,
        ),
        # Multitenancy: build HNSW per tenant (payload_m) instead of one global graph (m=0).
        # Every query MUST filter by tenant_id.
        hnsw_config=models.HnswConfigDiff(m=0, payload_m=16),
    )

    await client.create_payload_index(
        collection_name=name,
        field_name=TENANT_FIELD,
        field_schema=models.KeywordIndexParams(
            type=models.KeywordIndexType.KEYWORD,
            is_tenant=True,
        ),
    )
    # Needed for fast delete/filter of all chunks belonging to one document.
    await client.create_payload_index(
        collection_name=name,
        field_name=DOCUMENT_FIELD,
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    logger.info("Created Qdrant collection '%s' (dim=%s)", name, settings.embedding_dimension)


async def _validate_collection(client: AsyncQdrantClient, name: str) -> None:
    settings = get_settings()
    info = await client.get_collection(name)
    vectors = info.config.params.vectors
    if not isinstance(vectors, models.VectorParams):
        raise RuntimeError(
            f"Collection '{name}' uses named vectors; expected a single vector config."
        )
    if vectors.size != settings.embedding_dimension:
        raise RuntimeError(
            f"Collection '{name}' has dimension {vectors.size}, "
            f"but EMBEDDING_DIMENSION is {settings.embedding_dimension}. "
            "Use a new collection name or re-ingest."
        )