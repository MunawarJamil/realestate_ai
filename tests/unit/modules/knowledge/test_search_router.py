import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import create_autospec

import httpx
import pytest
from fastapi import FastAPI

from app.modules.knowledge.dependencies import get_retrieval_service
from app.modules.knowledge.exceptions import InvalidQueryError, RetrievalUnavailableError
from app.modules.knowledge.retrieval import RetrievalService, RetrievedChunk
from app.modules.knowledge.router import router
from app.modules.tenants.dependencies import get_current_tenant

TENANT = SimpleNamespace(id=uuid.uuid4())
URL = "/api/v1/knowledge/search"


@pytest.fixture
def retrieval() -> RetrievalService:
    mock: RetrievalService = create_autospec(RetrievalService, instance=True)
    return mock


@pytest.fixture
async def client(retrieval: RetrievalService) -> AsyncIterator[httpx.AsyncClient]:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_tenant] = lambda: TENANT
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as http_client:
        yield http_client


async def test_search_returns_ranked_results(
    client: httpx.AsyncClient, retrieval: RetrievalService
) -> None:
    document_id = uuid.uuid4()
    retrieval.search.return_value = [  # type: ignore[attr-defined]
        RetrievedChunk(
            document_id=document_id,
            document_title="Marina Brochure",
            page_number=2,
            chunk_index=4,
            text="3 bedroom villa",
            score=0.88,
        )
    ]

    response = await client.post(URL, json={"query": "villa", "limit": 3})

    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "document_id": str(document_id),
                "document_title": "Marina Brochure",
                "page_number": 2,
                "chunk_index": 4,
                "text": "3 bedroom villa",
                "score": 0.88,
            }
        ]
    }
    retrieval.search.assert_awaited_once_with(  # type: ignore[attr-defined]
        tenant_id=TENANT.id, query="villa", limit=3
    )


async def test_search_without_limit_passes_none(
    client: httpx.AsyncClient, retrieval: RetrievalService
) -> None:
    retrieval.search.return_value = []  # type: ignore[attr-defined]

    response = await client.post(URL, json={"query": "villa"})

    assert response.json() == {"results": []}
    assert retrieval.search.await_args.kwargs["limit"] is None  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "body",
    [{}, {"query": ""}, {"query": "x" * 1001}, {"query": "ok", "limit": 0}, {"query": "ok", "limit": 21}],
)
async def test_search_rejects_invalid_requests(
    client: httpx.AsyncClient, body: dict[str, Any]
) -> None:
    response = await client.post(URL, json=body)

    assert response.status_code == 422


async def test_blank_query_from_service_maps_to_422(
    client: httpx.AsyncClient, retrieval: RetrievalService
) -> None:
    retrieval.search.side_effect = InvalidQueryError("empty")  # type: ignore[attr-defined]

    response = await client.post(URL, json={"query": "   "})

    assert response.status_code == 422


async def test_outage_maps_to_503_with_retry_after(
    client: httpx.AsyncClient, retrieval: RetrievalService
) -> None:
    retrieval.search.side_effect = RetrievalUnavailableError("qdrant down")  # type: ignore[attr-defined]

    response = await client.post(URL, json={"query": "villa"})

    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert "qdrant" not in response.text