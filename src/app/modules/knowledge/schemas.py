import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.knowledge.enums import DocumentStatus


class KnowledgeDocumentRead(BaseModel):
    """Public view of a document. Storage key and checksum are deliberately not exposed."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    original_filename: str
    content_type: str
    size_bytes: int
    status: DocumentStatus
    error_message: str | None
    chunk_count: int
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentList(BaseModel):
    items: list[KnowledgeDocumentRead]
    total: int
    limit: int
    offset: int



class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    limit: int | None = Field(default=None, ge=1, le=20)


class SearchResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: uuid.UUID
    document_title: str
    page_number: int
    chunk_index: int
    text: str
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResultRead]