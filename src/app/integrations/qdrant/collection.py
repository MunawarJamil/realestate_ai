import logging

from qdrant_client import AsyncQdrantClient, models

from app.core.config import get_settings

logger = logging.getLogger(__name__)

TENANT_FIELD = "tenant_id"
DOCUMENT_FIELD = "document_id"
TEXT_FIELD = "text"



async def ensure_collection(client: AsyncQdrantClient) -> None:
    """Ensure the shared multi-tenant collection and all required indexes exist."""

    settings = get_settings()
    name = settings.qdrant_collection

    if await client.collection_exists(name):
        await _validate_collection(client, name)
        logger.info("Qdrant collection '%s' already exists", name)
    else:
        await client.create_collection(
            collection_name=name,
            vectors_config=models.VectorParams(
                size=settings.embedding_dimension,
                distance=models.Distance.COSINE,
            ),
            hnsw_config=models.HnswConfigDiff(
                m=0,
                payload_m=16,
            ),
        )
        logger.info(
            "Created Qdrant collection '%s' (dim=%s)",
            name,
            settings.embedding_dimension,
        )

    # Ensure indexes regardless of whether collection was newly created
    # or already existed. This also repairs partially initialized collections.

    await client.create_payload_index(
        collection_name=name,
        field_name=TENANT_FIELD,
        field_schema=models.KeywordIndexParams(
            type=models.KeywordIndexType.KEYWORD,
            is_tenant=True,
        ),
    )

    await client.create_payload_index(
        collection_name=name,
        field_name=DOCUMENT_FIELD,
        field_schema=models.PayloadSchemaType.KEYWORD,
    )

    await client.create_payload_index(
        collection_name=name,
        field_name=TEXT_FIELD,
        field_schema=models.TextIndexParams(
            type=models.TextIndexType.TEXT,
            tokenizer=models.TokenizerType.WORD,
            min_token_len=2,
            max_token_len=30,
            lowercase=True,
        ),
    )

    logger.info("Qdrant indexes ensured for collection '%s'", name)



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