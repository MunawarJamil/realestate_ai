from app.modules.knowledge.schemas import SearchResultRead
from app.modules.knowledge.retrieval import RetrievalService
from app.modules.knowledge.dependencies import get_retrieval_service
from app.modules.knowledge.schemas import SearchRequest
from app.modules.knowledge.schemas import SearchResponse
import logging
import uuid
from typing import Any, Final

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.core.config import Settings, get_settings
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
    InvalidQueryError, RetrievalUnavailableError,
)
from app.modules.knowledge.models import KnowledgeDocument
from app.modules.knowledge.schemas import KnowledgeDocumentList, KnowledgeDocumentRead
from app.modules.knowledge.service import KnowledgeService
from app.modules.tenants.dependencies import get_current_tenant
from app.modules.tenants.models import Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_STATUS_BY_ERROR: Final[tuple[tuple[type[KnowledgeError], int], ...]] = (
    (UnsupportedContentTypeError, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE),
    (InvalidDocumentError, status.HTTP_422_UNPROCESSABLE_ENTITY),
    (FileTooLargeError, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE),
    (DuplicateDocumentError, status.HTTP_409_CONFLICT),
    (DocumentNotFoundError, status.HTTP_404_NOT_FOUND),
    (QueueUnavailableError, status.HTTP_503_SERVICE_UNAVAILABLE),
    (InvalidQueryError, status.HTTP_422_UNPROCESSABLE_ENTITY),
    (RetrievalUnavailableError, status.HTTP_503_SERVICE_UNAVAILABLE),
)


def _to_http_error(exc: KnowledgeError) -> HTTPException:
    status_code = next(
        (code for error_type, code in _STATUS_BY_ERROR if isinstance(exc, error_type)), None
    )
    if status_code is None:
        logger.error("Unmapped knowledge error", exc_info=exc)
        return HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Unexpected error.")

    detail: Any = str(exc)
    headers: dict[str, str] | None = None
    if isinstance(exc, DuplicateDocumentError):
        detail = {
            "message": str(exc),
            "existing_document_id": str(exc.existing_id) if exc.existing_id else None,
        }
    elif isinstance(exc, UnsupportedContentTypeError):
        detail = f"{exc} Supported formats: PDF, TXT, Markdown."
    elif isinstance(exc, QueueUnavailableError):
        detail = "Document processing is temporarily unavailable. Please retry shortly."
        headers = {"Retry-After": "5"}
    elif isinstance(exc, RetrievalUnavailableError):
        detail = "Search is temporarily unavailable. Please retry shortly."
        headers = {"Retry-After": "5"}
    return HTTPException(status_code, detail, headers=headers)






@router.post(
    "/documents",
    response_model=KnowledgeDocumentRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None, max_length=255),
    tenant: Tenant = Depends(get_current_tenant),
    service: KnowledgeService = Depends(get_knowledge_service),
    settings: Settings = Depends(get_settings),
) -> KnowledgeDocument:
    # Read at most limit + 1 bytes: enough to detect an oversized file without buffering all of it.
    data = await file.read(settings.max_upload_bytes + 1)
    try:
        return await service.upload(
            tenant_id=tenant.id,
            filename=file.filename,
            declared_content_type=file.content_type,
            data=data,
            title=title,
        )
    except KnowledgeError as exc:
        raise _to_http_error(exc) from exc



@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    payload: SearchRequest,
    tenant: Tenant = Depends(get_current_tenant),
    retrieval: RetrievalService = Depends(get_retrieval_service),
) -> SearchResponse:
    try:
        chunks = await retrieval.search(
            tenant_id=tenant.id, query=payload.query, limit=payload.limit
        )
    except KnowledgeError as exc:
        raise _to_http_error(exc) from exc
    return SearchResponse(results=[SearchResultRead.model_validate(chunk) for chunk in chunks])


@router.get("/documents", response_model=KnowledgeDocumentList)
async def list_documents(
    document_status: DocumentStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    tenant: Tenant = Depends(get_current_tenant),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeDocumentList:
    items, total = await service.list_documents(
        tenant_id=tenant.id, status=document_status, limit=limit, offset=offset
    )
    return KnowledgeDocumentList(
        items=[KnowledgeDocumentRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/documents/{document_id}", response_model=KnowledgeDocumentRead)
async def get_document(
    document_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeDocument:
    try:
        return await service.get(tenant_id=tenant.id, document_id=document_id)
    except KnowledgeError as exc:
        raise _to_http_error(exc) from exc


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> None:
    try:
        await service.delete(tenant_id=tenant.id, document_id=document_id)
    except KnowledgeError as exc:
        raise _to_http_error(exc) from exc