from app.modules.knowledge.vector_store import ScoredChunk
import uuid
from unittest.mock import create_autospec

import pytest
from qdrant_client import AsyncQdrantClient, models
from types import SimpleNamespace
from app.integrations.qdrant.collection import DOCUMENT_FIELD, TENANT_FIELD
from app.modules.knowledge.chunking import TextChunk
from app.modules.knowledge.vector_store import (
    CHUNK_INDEX_FIELD,
    PAGE_NUMBER_FIELD,
    TEXT_FIELD,
    ChunkVectorStore,
    chunk_point_id,
)

COLLECTION = "test_chunks"
TENANT_ID = uuid.uuid4()
DOCUMENT_ID = uuid.uuid4()


@pytest.fixture
def client() -> AsyncQdrantClient:
    mock: AsyncQdrantClient = create_autospec(AsyncQdrantClient, instance=True)
    return mock


@pytest.fixture
def store(client: AsyncQdrantClient) -> ChunkVectorStore:
    return ChunkVectorStore(client, COLLECTION)


def test_chunk_point_id_is_deterministic() -> None:
    assert chunk_point_id(DOCUMENT_ID, 3) == chunk_point_id(DOCUMENT_ID, 3)


def test_chunk_point_id_differs_per_chunk_and_per_document() -> None:
    assert chunk_point_id(DOCUMENT_ID, 0) != chunk_point_id(DOCUMENT_ID, 1)
    assert chunk_point_id(DOCUMENT_ID, 0) != chunk_point_id(uuid.uuid4(), 0)


async def test_upsert_builds_points_with_tenant_scoped_payload(
    store: ChunkVectorStore, client: AsyncQdrantClient
) -> None:
    chunks = [
        TextChunk(index=0, text="first", page_number=1),
        TextChunk(index=1, text="second", page_number=2),
    ]

    await store.upsert_chunks(
        tenant_id=TENANT_ID,
        document_id=DOCUMENT_ID,
        chunks=chunks,
        vectors=[[0.1, 0.2], [0.3, 0.4]],
    )

    client.upsert.assert_awaited_once()  # type: ignore[attr-defined]
    kwargs = client.upsert.await_args.kwargs  # type: ignore[attr-defined]
    assert kwargs["collection_name"] == COLLECTION
    assert kwargs["wait"] is True
    points = kwargs["points"]
    assert [p.id for p in points] == [str(chunk_point_id(DOCUMENT_ID, i)) for i in (0, 1)]
    assert points[1].vector == [0.3, 0.4]
    assert points[1].payload == {
        TENANT_FIELD: str(TENANT_ID),
        DOCUMENT_FIELD: str(DOCUMENT_ID),
        CHUNK_INDEX_FIELD: 1,
        PAGE_NUMBER_FIELD: 2,
        TEXT_FIELD: "second",
    }


async def test_upsert_with_no_chunks_does_not_call_qdrant(
    store: ChunkVectorStore, client: AsyncQdrantClient
) -> None:
    await store.upsert_chunks(tenant_id=TENANT_ID, document_id=DOCUMENT_ID, chunks=[], vectors=[])

    client.upsert.assert_not_awaited()  # type: ignore[attr-defined]


async def test_upsert_rejects_chunk_vector_count_mismatch(
    store: ChunkVectorStore, client: AsyncQdrantClient
) -> None:
    with pytest.raises(ValueError, match="vectors"):
        await store.upsert_chunks(
            tenant_id=TENANT_ID,
            document_id=DOCUMENT_ID,
            chunks=[TextChunk(index=0, text="a", page_number=1)],
            vectors=[],
        )

    client.upsert.assert_not_awaited()  # type: ignore[attr-defined]


def _delete_conditions(client: AsyncQdrantClient) -> list[models.FieldCondition]:
    kwargs = client.delete.await_args.kwargs  # type: ignore[attr-defined]
    assert kwargs["collection_name"] == COLLECTION
    assert kwargs["wait"] is True
    return list(kwargs["points_selector"].filter.must)


async def test_delete_document_is_scoped_by_tenant_and_document(
    store: ChunkVectorStore, client: AsyncQdrantClient
) -> None:
    await store.delete_document(tenant_id=TENANT_ID, document_id=DOCUMENT_ID)

    conditions = _delete_conditions(client)
    matches = {
        c.key: c.match.value
        for c in conditions
        if isinstance(c.match, models.MatchValue)
    }
    assert matches == {TENANT_FIELD: str(TENANT_ID), DOCUMENT_FIELD: str(DOCUMENT_ID)}


async def test_delete_stale_chunks_filters_by_tenant_document_and_index(
    store: ChunkVectorStore, client: AsyncQdrantClient
) -> None:
    await store.delete_stale_chunks(tenant_id=TENANT_ID, document_id=DOCUMENT_ID, keep_count=5)

    conditions = _delete_conditions(client)
    keys = {c.key for c in conditions}
    assert keys == {TENANT_FIELD, DOCUMENT_FIELD, CHUNK_INDEX_FIELD}
    index_condition = next(c for c in conditions if c.key == CHUNK_INDEX_FIELD)
    assert index_condition.range is not None
    assert index_condition.range.gte == 5




def make_point(score: float, payload: dict[str, object] | None) -> SimpleNamespace:
    return SimpleNamespace(id=str(uuid.uuid4()), score=score, payload=payload)


def valid_payload(index: int = 0, text: str = "chunk") -> dict[str, object]:
    return {
        TENANT_FIELD: str(TENANT_ID),
        DOCUMENT_FIELD: str(DOCUMENT_ID),
        CHUNK_INDEX_FIELD: index,
        PAGE_NUMBER_FIELD: 2,
        TEXT_FIELD: text,
    }


async def test_search_is_always_filtered_by_tenant(
    store: ChunkVectorStore, client: AsyncQdrantClient
) -> None:
    client.query_points.return_value = SimpleNamespace(points=[])  # type: ignore[attr-defined]

    await store.search(tenant_id=TENANT_ID, vector=[0.1, 0.2], limit=5, score_threshold=0.3)

    kwargs = client.query_points.await_args.kwargs  # type: ignore[attr-defined]
    assert kwargs["collection_name"] == COLLECTION
    assert kwargs["query"] == [0.1, 0.2]
    assert kwargs["limit"] == 5
    assert kwargs["score_threshold"] == 0.3
    assert kwargs["with_payload"] is True
    assert kwargs["with_vectors"] is False
    conditions = kwargs["query_filter"].must
    assert [(c.key, c.match.value) for c in conditions] == [(TENANT_FIELD, str(TENANT_ID))]


async def test_search_maps_points_to_scored_chunks(
    store: ChunkVectorStore, client: AsyncQdrantClient
) -> None:
    client.query_points.return_value = SimpleNamespace(  # type: ignore[attr-defined]
        points=[make_point(0.91, valid_payload(3, "villa text"))]
    )

    chunks = await store.search(tenant_id=TENANT_ID, vector=[0.1], limit=5)

    assert chunks == [
        ScoredChunk(
            document_id=DOCUMENT_ID, chunk_index=3, page_number=2, text="villa text", score=0.91
        )
    ]


@pytest.mark.parametrize(
    "bad_payload",
    [None, {}, {**valid_payload(), DOCUMENT_FIELD: "not-a-uuid"}, {TENANT_FIELD: "x"}],
)
async def test_search_skips_malformed_points(
    store: ChunkVectorStore, client: AsyncQdrantClient, bad_payload: dict[str, object] | None
) -> None:
    client.query_points.return_value = SimpleNamespace(  # type: ignore[attr-defined]
        points=[make_point(0.5, bad_payload), make_point(0.4, valid_payload(1))]
    )
    chunks = await store.search(tenant_id=TENANT_ID, vector=[0.1], limit=5)
    assert [chunk.chunk_index for chunk in chunks] == [1]




def test_reciprocal_rank_fusion() -> None:
    from app.modules.knowledge.vector_store import _reciprocal_rank_fusion

    doc1, doc2, doc3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    dense = [
        ScoredChunk(document_id=doc1, chunk_index=0, page_number=1, text="dense top", score=0.9),
        ScoredChunk(document_id=doc2, chunk_index=0, page_number=1, text="dense 2nd", score=0.8),
    ]
    keyword = [
        ScoredChunk(document_id=doc3, chunk_index=0, page_number=1, text="kw top", score=1.0),
        ScoredChunk(document_id=doc1, chunk_index=0, page_number=1, text="dense top", score=1.0),
    ]

    fused = _reciprocal_rank_fusion(dense, keyword)

    # doc1 is in BOTH dense and keyword rankings, so it must be ranked #1
    assert fused[0].document_id == doc1
    assert len(fused) == 3


async def test_hybrid_search_combines_dense_and_keyword(
    store: ChunkVectorStore, client: AsyncQdrantClient
) -> None:
    # Mock dense query_points
    client.query_points.return_value = SimpleNamespace(  # type: ignore[attr-defined]
        points=[make_point(0.85, valid_payload(0, "dense match"))]
    )
    # Mock keyword scroll
    keyword_record = SimpleNamespace(
        id=str(uuid.uuid4()),
        payload=valid_payload(1, "exact 402 keyword match"),
    )
    client.scroll.return_value = ([keyword_record], None)  # type: ignore[attr-defined]

    results = await store.hybrid_search(
        tenant_id=TENANT_ID,
        vector=[0.1, 0.2],
        query_text="Villa 402",
        limit=5,
    )

    assert len(results) == 2
    indices = {c.chunk_index for c in results}
    assert indices == {0, 1}
    client.scroll.assert_awaited_once()  # type: ignore[attr-defined]