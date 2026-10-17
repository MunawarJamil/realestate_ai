import uuid
from collections.abc import Sequence
from typing import Final
import logging
from qdrant_client import AsyncQdrantClient, models
from dataclasses import dataclass
from app.integrations.qdrant.collection import DOCUMENT_FIELD, TENANT_FIELD
from app.modules.knowledge.chunking import TextChunk

CHUNK_INDEX_FIELD: Final = "chunk_index"
PAGE_NUMBER_FIELD: Final = "page_number"
TEXT_FIELD: Final = "text"
logger = logging.getLogger(__name__)

def chunk_point_id(document_id: uuid.UUID, chunk_index: int) -> uuid.UUID:
    """Deterministic point id, so re-ingesting a document overwrites instead of duplicating."""
    return uuid.uuid5(document_id, str(chunk_index))


@dataclass(frozen=True, slots=True)
class ScoredChunk:
    document_id: uuid.UUID
    chunk_index: int
    page_number: int
    text: str
    score: float


def _to_scored_chunk(point: models.ScoredPoint) -> ScoredChunk | None:
    payload = point.payload or {}
    try:
        return ScoredChunk(
            document_id=uuid.UUID(str(payload[DOCUMENT_FIELD])),
            chunk_index=int(payload[CHUNK_INDEX_FIELD]),
            page_number=int(payload[PAGE_NUMBER_FIELD]),
            text=str(payload[TEXT_FIELD]),
            score=point.score,
        )
    except (KeyError, ValueError, TypeError):
        logger.warning("Skipping malformed Qdrant point %s", point.id)
        return None



class ChunkVectorStore:
    """All Qdrant access for knowledge chunks. Every operation is scoped by tenant_id."""

    def __init__(self, client: AsyncQdrantClient, collection: str) -> None:
        self._client = client
        self._collection = collection

    async def upsert_chunks(
        self,
        *,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        chunks: Sequence[TextChunk],
        vectors: Sequence[Sequence[float]],
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError(f"Got {len(vectors)} vectors for {len(chunks)} chunks.")
        if not chunks:
            return

        points = [
            models.PointStruct(
                id=str(chunk_point_id(document_id, chunk.index)),
                vector=list(vector),
                payload={
                    TENANT_FIELD: str(tenant_id),
                    DOCUMENT_FIELD: str(document_id),
                    CHUNK_INDEX_FIELD: chunk.index,
                    PAGE_NUMBER_FIELD: chunk.page_number,
                    TEXT_FIELD: chunk.text,
                },
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        # wait=True: a document is only marked "ready" once its vectors are searchable.
        await self._client.upsert(collection_name=self._collection, points=points, wait=True)

    async def delete_stale_chunks(
        self, *, tenant_id: uuid.UUID, document_id: uuid.UUID, keep_count: int
    ) -> None:
        """Remove chunks left over from an earlier, longer version of the same document."""
        stale = models.FieldCondition(key=CHUNK_INDEX_FIELD, range=models.Range(gte=keep_count))
        await self._delete(self._document_filter(tenant_id, document_id, stale))

    async def delete_document(self, *, tenant_id: uuid.UUID, document_id: uuid.UUID) -> None:
        await self._delete(self._document_filter(tenant_id, document_id))

    async def _delete(self, selector_filter: models.Filter) -> None:
        await self._client.delete(
            collection_name=self._collection,
            points_selector=models.FilterSelector(filter=selector_filter),
            wait=True,
        )


    async def search(
        self,
        *,
        tenant_id: uuid.UUID,
        vector: Sequence[float],
        limit: int,
        score_threshold: float | None = None,
    ) -> list[ScoredChunk]:
        """Nearest chunks for one tenant. The tenant filter is mandatory and not optional."""
        response = await self._client.query_points(
            collection_name=self._collection,
            query=list(vector),
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key=TENANT_FIELD, match=models.MatchValue(value=str(tenant_id))
                    )
                ]
            ),
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=False,
        )
        chunks = (_to_scored_chunk(point) for point in response.points)
        return [chunk for chunk in chunks if chunk is not None]


    @staticmethod
    def _document_filter(
        tenant_id: uuid.UUID, document_id: uuid.UUID, *extra: models.Condition
    ) -> models.Filter:
        return models.Filter(
            must=[
                models.FieldCondition(key=TENANT_FIELD, match=models.MatchValue(value=str(tenant_id))),
                models.FieldCondition(
                    key=DOCUMENT_FIELD, match=models.MatchValue(value=str(document_id))
                ),
                *extra,
            ]
        )