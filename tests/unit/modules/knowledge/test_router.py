import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import create_autospec

import httpx
import pytest
from fastapi import FastAPI

from app.core.config import get_settings
from app.modules.knowledge.dependencies import get_knowledge_service
from app.modules.knowledge.enums import DocumentStatus
from app.modules.knowledge.exceptions import (
    DocumentNotFoundError,
    DuplicateDocumentError,
    FileTooLargeError,
    InvalidDocumentError,
    KnowledgeError,
    QueueUnavailableError,
    UnsupportedContentTypeError,
)
from app.modules.knowledge.router import router
from app.modules.knowledge.service import KnowledgeService
from app.modules.tenants.dependencies import get_current_tenant

TENANT = SimpleNamespace(id=uuid.uuid4())
MAX_BYTES = 16
URL = "/api/v1/knowledge/documents"
NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)


def make_document(**overrides: Any) -> SimpleNamespace:
    values: dict[str, Any] = {
        "id": uuid.uuid4(),
        "title": "Marina Villa",
        "original_filename": "villa.txt",
        "content_type": "text/plain",
        "size_bytes": 12,
        "status": DocumentStatus.PENDING,
        "error_message": None,
        "chunk_count": 0,
        "processed_at": None,
        "created_at": NOW,
        "updated_at": NOW,
        # internal fields that must never leak into responses
        "storage_key": "tenant/doc",
        "checksum_sha256": "abc123",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture
def service() -> KnowledgeService:
    mock: KnowledgeService = create_autospec(KnowledgeService, instance=True)
    return mock


@pytest.fixture
async def client(service: KnowledgeService) -> AsyncIterator[httpx.AsyncClient]:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_tenant] = lambda: TENANT
    app.dependency_overrides[get_knowledge_service] = lambda: service
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(max_upload_bytes=MAX_BYTES)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as http_client:
        yield http_client


# --- upload -------------------------------------------------------------------------------


async def test_upload_returns_202_with_public_fields_only(
    client: httpx.AsyncClient, service: KnowledgeService
) -> None:
    document = make_document()
    service.upload.return_value = document  # type: ignore[attr-defined]

    response = await client.post(
        URL,
        files={"file": ("villa.txt", b"hello", "text/plain")},
        data={"title": "Marina Villa"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["id"] == str(document.id)
    assert body["status"] == "pending"
    assert "storage_key" not in body
    assert "checksum_sha256" not in body
    service.upload.assert_awaited_once_with(  # type: ignore[attr-defined]
        tenant_id=TENANT.id,
        filename="villa.txt",
        declared_content_type="text/plain",
        data=b"hello",
        title="Marina Villa",
    )


async def test_upload_reads_at_most_limit_plus_one_bytes(
    client: httpx.AsyncClient, service: KnowledgeService
) -> None:
    service.upload.return_value = make_document()  # type: ignore[attr-defined]

    await client.post(URL, files={"file": ("big.txt", b"x" * 1000, "text/plain")})

    sent = service.upload.await_args.kwargs["data"]  # type: ignore[attr-defined]
    assert len(sent) == MAX_BYTES + 1


async def test_upload_without_file_is_rejected(client: httpx.AsyncClient) -> None:
    response = await client.post(URL, data={"title": "no file"})

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (UnsupportedContentTypeError("image/png"), 415),
        (InvalidDocumentError("The file is not a valid PDF."), 422),
        (FileTooLargeError(MAX_BYTES), 413),
        (QueueUnavailableError("redis down"), 503),
    ],
)
async def test_upload_maps_domain_errors_to_http_status(
    client: httpx.AsyncClient,
    service: KnowledgeService,
    error: KnowledgeError,
    expected_status: int,
) -> None:
    service.upload.side_effect = error  # type: ignore[attr-defined]

    response = await client.post(URL, files={"file": ("a.txt", b"hi", "text/plain")})

    assert response.status_code == expected_status


async def test_duplicate_upload_returns_409_with_existing_document_id(
    client: httpx.AsyncClient, service: KnowledgeService
) -> None:
    existing_id = uuid.uuid4()
    service.upload.side_effect = DuplicateDocumentError(existing_id)  # type: ignore[attr-defined]

    response = await client.post(URL, files={"file": ("a.txt", b"hi", "text/plain")})

    assert response.status_code == 409
    assert response.json()["detail"]["existing_document_id"] == str(existing_id)


async def test_queue_outage_tells_client_to_retry(
    client: httpx.AsyncClient, service: KnowledgeService
) -> None:
    service.upload.side_effect = QueueUnavailableError("redis down")  # type: ignore[attr-defined]

    response = await client.post(URL, files={"file": ("a.txt", b"hi", "text/plain")})

    assert response.headers["retry-after"] == "5"
    assert "redis" not in response.text


async def test_unmapped_error_returns_generic_500_without_leaking_details(
    client: httpx.AsyncClient, service: KnowledgeService
) -> None:
    service.upload.side_effect = KnowledgeError("internal secret")  # type: ignore[attr-defined]

    response = await client.post(URL, files={"file": ("a.txt", b"hi", "text/plain")})

    assert response.status_code == 500
    assert "secret" not in response.text


# --- list ---------------------------------------------------------------------------------


async def test_list_uses_default_pagination(
    client: httpx.AsyncClient, service: KnowledgeService
) -> None:
    service.list_documents.return_value = ([make_document()], 1)  # type: ignore[attr-defined]

    response = await client.get(URL)

    assert response.status_code == 200
    
    assert response.json()["total"] == 1
    assert response.json()["limit"] == 20
    service.list_documents.assert_awaited_once_with(  # type: ignore[attr-defined]
        tenant_id=TENANT.id, status=None, limit=20, offset=0
    )


async def test_list_passes_filters_and_returns_page_metadata(
    client: httpx.AsyncClient, service: KnowledgeService
) -> None:
    items = [make_document(status=DocumentStatus.READY), make_document(status=DocumentStatus.READY)]
    service.list_documents.return_value = (items, 5)  # type: ignore[attr-defined]

    response = await client.get(URL, params={"status": "ready", "limit": 2, "offset": 2})

    body = response.json()
    assert [item["status"] for item in body["items"]] == ["ready", "ready"]
    assert (body["total"], body["limit"], body["offset"]) == (5, 2, 2)
    service.list_documents.assert_awaited_once_with(  # type: ignore[attr-defined]
        tenant_id=TENANT.id, status=DocumentStatus.READY, limit=2, offset=2
    )


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"status": "bogus"}],
)
async def test_list_rejects_invalid_query_parameters(
    client: httpx.AsyncClient, params: dict[str, Any]
) -> None:
    response = await client.get(URL, params=params)

    assert response.status_code == 422


# --- get / delete -------------------------------------------------------------------------


async def test_get_returns_document(client: httpx.AsyncClient, service: KnowledgeService) -> None:
    document = make_document(status=DocumentStatus.READY, chunk_count=7)
    service.get.return_value = document  # type: ignore[attr-defined]

    response = await client.get(f"{URL}/{document.id}")

    assert response.status_code == 200
    assert response.json()["chunk_count"] == 7
    service.get.assert_awaited_once_with(  # type: ignore[attr-defined]
        tenant_id=TENANT.id, document_id=document.id
    )


async def test_get_unknown_document_returns_404(
    client: httpx.AsyncClient, service: KnowledgeService
) -> None:
    document_id = uuid.uuid4()
    service.get.side_effect = DocumentNotFoundError(document_id)  # type: ignore[attr-defined]

    response = await client.get(f"{URL}/{document_id}")

    assert response.status_code == 404


async def test_get_with_malformed_id_returns_422(client: httpx.AsyncClient) -> None:
    response = await client.get(f"{URL}/not-a-uuid")

    assert response.status_code == 422


async def test_delete_returns_204(client: httpx.AsyncClient, service: KnowledgeService) -> None:
    document_id = uuid.uuid4()

    response = await client.delete(f"{URL}/{document_id}")

    assert response.status_code == 204
    assert response.content == b""
    service.delete.assert_awaited_once_with(  # type: ignore[attr-defined]
        tenant_id=TENANT.id, document_id=document_id
    )


async def test_delete_unknown_document_returns_404(
    client: httpx.AsyncClient, service: KnowledgeService
) -> None:
    document_id = uuid.uuid4()
    service.delete.side_effect = DocumentNotFoundError(document_id)  # type: ignore[attr-defined]

    response = await client.delete(f"{URL}/{document_id}")

    assert response.status_code == 404




