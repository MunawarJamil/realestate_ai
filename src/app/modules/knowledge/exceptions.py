import uuid

class KnowledgeError(Exception):
    """Base class for knowledge-module domain errors."""


class UnsupportedContentTypeError(KnowledgeError):
    def __init__(self, content_type: str) -> None:
        super().__init__(f"Unsupported content type: {content_type!r}")
        self.content_type = content_type


class ExtractionError(KnowledgeError):
    """The file is corrupt, encrypted, or otherwise unreadable."""


class EmptyDocumentError(KnowledgeError):
    """No extractable text (e.g. a scanned PDF without a text layer)."""

class DocumentTooLargeError(KnowledgeError):
    def __init__(self, chunk_count: int, limit: int) -> None:
        super().__init__(f"Document produces {chunk_count} chunks; the limit is {limit}.")
        self.chunk_count = chunk_count
        self.limit = limit
    
class StorageFileNotFoundError(KnowledgeError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Stored file not found: {key!r}")
        self.key = key


class InvalidDocumentError(KnowledgeError):
    """The upload is empty or its content does not match its declared type."""


class FileTooLargeError(KnowledgeError):
    def __init__(self, limit_bytes: int) -> None:
        super().__init__(f"File exceeds the {limit_bytes // (1024 * 1024)} MB upload limit.")
        self.limit_bytes = limit_bytes


class DuplicateDocumentError(KnowledgeError):
    def __init__(self, existing_id: uuid.UUID | None) -> None:
        super().__init__("This file has already been uploaded.")
        self.existing_id = existing_id


class DocumentNotFoundError(KnowledgeError):
    def __init__(self, document_id: uuid.UUID) -> None:
        super().__init__(f"Document {document_id} not found.")
        self.document_id = document_id


class QueueUnavailableError(KnowledgeError):
    """The job queue could not be reached; the upload was rolled back."""


class InvalidQueryError(KnowledgeError):
    """The search query is empty."""


class RetrievalUnavailableError(KnowledgeError):
    """Embedding provider or vector store could not be reached."""