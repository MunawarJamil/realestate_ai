import hashlib
import uuid
from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest

from app.modules.knowledge.enums import DocumentStatus
from app.modules.knowledge.exceptions import (
    DocumentNotFoundError,
    DuplicateDocumentError,
    FileTooLargeError,
    InvalidDocumentError,
    QueueUnavailableError,
    UnsupportedContentTypeError,
)
from app.modules.knowledge.models import KnowledgeDocument
from app.modules.knowledge.repository import KnowledgeDocumentRepository
from app.modules.knowledge.service import KnowledgeService
from app.modules.knowledge.storage import build_storage_key
from app.modules.knowledge.vector_store import ChunkVectorStore

TENANT_ID = uuid.uuid4()
MAX_BYTES = 1024
DATA = b"3 bedroom villa in Dubai Marina with sea view"


class Events:
    """Shared, ordered log so tests can assert *when* things happened."""

    def __init__(self) -> None:
        self.log: list[str] = []


class FakeStorage:
    def __init__(self, events: Events) -> None:
        self._events = events
        self.saved: dict[str, bytes] = {}
        self.deleted: list[str] = []

    async def save(self, *, key: str, data: bytes) -> None:
        self._events.log.append("save_file")
        self.saved[key] = data

    async def read(self, key: str) -> bytes:
        return self.saved[key]

    async def delete(self, key: str) -> None:
        self._events.log.append("delete_file")
        self.deleted.append(key)


class FakeQueue:
    def __init__(self, events: Events, *, error: Exception | None = None) -> None:
        self._events = events
        self._error = error
        self.enqueued: list[tuple[uuid.UUID, uuid.UUID]] = []

    async def enqueue(self, *, tenant_id: uuid.UUID, document_id: uuid.UUID) -> None:
        self._events.log.append("enqueue")
        if self._error is not None:
            raise self._error
        self.enqueued.append((tenant_id, document_id))


@pytest.fixture
def events() -> Events:
    return Events()


@pytest.fixture
def storage(events: Events) -> FakeStorage:
    return FakeStorage(events)


@pytest.fixture
def queue(events: Events) -> FakeQueue:
    return FakeQueue(events)


@pytest.fixture
def repository(events: Events) -> KnowledgeDocumentRepository:
    repo: KnowledgeDocumentRepository = create_autospec(KnowledgeDocumentRepository, instance=True)

    async def add(document: KnowledgeDocument) -> KnowledgeDocument:
        events.log.append("add")
        return document

    async def commit() -> None:
        events.log.append("commit")

    async def delete(*, tenant_id: uuid.UUID, document_id: uuid.UUID) -> bool:
        events.log.append("delete_row")
        return True

    repo.get_by_checksum.return_value = None  # type: ignore[attr-defined]
    repo.add.side_effect = add  # type: ignore[attr-defined]
    repo.commit.side_effect = commit  # type: ignore[attr-defined]
    repo.delete.side_effect = delete  # type: ignore[attr-defined]
    return repo


@pytest.fixture
def store(events: Events) -> ChunkVectorStore:
    mock: ChunkVectorStore = create_autospec(ChunkVectorStore, instance=True)

    async def delete_document(*, tenant_id: uuid.UUID, document_id: uuid.UUID) -> None:
        events.log.append("delete_vectors")

    mock.delete_document.side_effect = delete_document  # type: ignore[attr-defined]
    return mock


@pytest.fixture
def service(
    repository: KnowledgeDocumentRepository,
    storage: FakeStorage,
    store: ChunkVectorStore,
    queue: FakeQueue,
) -> KnowledgeService:
    return KnowledgeService(
        repository=repository,
        storage=storage,
        store=store,
        queue=queue,
        max_upload_bytes=MAX_BYTES,
    )


async def upload(
    service: KnowledgeService,
    *,
    filename: str | None = "villa.txt",
    declared: str | None = "text/plain",
    data: bytes = DATA,
    title: str | None = None,
) -> KnowledgeDocument:
    return await service.upload(
        tenant_id=TENANT_ID,
        filename=filename,
        declared_content_type=declared,
        data=data,
        title=title,
    )


# --- upload: success ----------------------------------------------------------------------


async def test_upload_builds_document_from_file_metadata(
    service: KnowledgeService, storage: FakeStorage
) -> None:
    document = await upload(service, filename="../Marina Villa.txt")

    assert document.tenant_id == TENANT_ID
    assert document.title == "Marina Villa"
    assert document.original_filename == "Marina Villa.txt"
    assert document.content_type == "text/plain"
    assert document.size_bytes == len(DATA)
    assert document.checksum_sha256 == hashlib.sha256(DATA).hexdigest()
    assert document.storage_key == build_storage_key(TENANT_ID, document.id)
    assert storage.saved == {document.storage_key: DATA}


async def test_upload_uses_explicit_title(service: KnowledgeService) -> None:
    document = await upload(service, title="  Sea View Villa  ")

    assert document.title == "Sea View Villa"


async def test_upload_orders_file_row_commit_then_enqueue(
    service: KnowledgeService, events: Events, queue: FakeQueue
) -> None:
    document = await upload(service)

    assert events.log == ["save_file", "add", "commit", "enqueue"]
    assert queue.enqueued == [(TENANT_ID, document.id)]


# --- upload: validation -------------------------------------------------------------------


async def test_empty_file_is_rejected(service: KnowledgeService, storage: FakeStorage) -> None:
    with pytest.raises(InvalidDocumentError):
        await upload(service, data=b"")

    assert storage.saved == {}


async def test_oversized_file_is_rejected(service: KnowledgeService, storage: FakeStorage) -> None:
    with pytest.raises(FileTooLargeError) as exc_info:
        await upload(service, data=b"x" * (MAX_BYTES + 1))

    assert exc_info.value.limit_bytes == MAX_BYTES
    assert storage.saved == {}


async def test_unsupported_type_is_rejected(service: KnowledgeService) -> None:
    with pytest.raises(UnsupportedContentTypeError):
        await upload(service, filename="photo.png", declared="image/png")


async def test_fake_pdf_is_rejected(service: KnowledgeService, storage: FakeStorage) -> None:
    with pytest.raises(InvalidDocumentError):
        await upload(service, filename="fake.pdf", declared="application/pdf", data=b"not a pdf")

    assert storage.saved == {}


# --- upload: duplicates -------------------------------------------------------------------


async def test_known_checksum_is_rejected_before_anything_is_stored(
    service: KnowledgeService,
    repository: KnowledgeDocumentRepository,
    storage: FakeStorage,
    queue: FakeQueue,
) -> None:
    existing_id = uuid.uuid4()
    repository.get_by_checksum.return_value = SimpleNamespace(id=existing_id)  # type: ignore[attr-defined]

    with pytest.raises(DuplicateDocumentError) as exc_info:
        await upload(service)

    assert exc_info.value.existing_id == existing_id
    assert storage.saved == {}
    assert queue.enqueued == []


async def test_lost_race_discards_file_and_reports_the_winner(
    service: KnowledgeService,
    repository: KnowledgeDocumentRepository,
    storage: FakeStorage,
    queue: FakeQueue,
    events: Events,
) -> None:
    winner_id = uuid.uuid4()
    repository.get_by_checksum.side_effect = [None, SimpleNamespace(id=winner_id)]  # type: ignore[attr-defined]
    repository.add.side_effect = None  # type: ignore[attr-defined]
    repository.add.return_value = None  # type: ignore[attr-defined]

    with pytest.raises(DuplicateDocumentError) as exc_info:
        await upload(service)

    assert exc_info.value.existing_id == winner_id
    assert len(storage.deleted) == 1
    assert "commit" not in events.log
    assert queue.enqueued == []


# --- upload: failures ---------------------------------------------------------------------


async def test_database_failure_discards_the_stored_file(
    service: KnowledgeService,
    repository: KnowledgeDocumentRepository,
    storage: FakeStorage,
    queue: FakeQueue,
) -> None:
    repository.add.side_effect = RuntimeError("db down")  # type: ignore[attr-defined]

    with pytest.raises(RuntimeError, match="db down"):
        await upload(service)

    assert list(storage.saved) == storage.deleted
    assert queue.enqueued == []


async def test_queue_failure_rolls_back_row_and_file(
    repository: KnowledgeDocumentRepository,
    storage: FakeStorage,
    store: ChunkVectorStore,
    events: Events,
) -> None:
    failing_queue = FakeQueue(events, error=QueueUnavailableError("redis down"))
    service = KnowledgeService(
        repository=repository,
        storage=storage,
        store=store,
        queue=failing_queue,
        max_upload_bytes=MAX_BYTES,
    )

    with pytest.raises(QueueUnavailableError):
        await upload(service)

    assert events.log == [
        "save_file", "add", "commit", "enqueue", "delete_row", "commit", "delete_file",
    ]
    assert list(storage.saved) == storage.deleted


# --- get / list ---------------------------------------------------------------------------


async def test_get_returns_document(
    service: KnowledgeService, repository: KnowledgeDocumentRepository
) -> None:
    document_id = uuid.uuid4()
    stored = SimpleNamespace(id=document_id)
    repository.get.return_value = stored  # type: ignore[attr-defined]

    assert await service.get(tenant_id=TENANT_ID, document_id=document_id) is stored
    repository.get.assert_awaited_once_with(  # type: ignore[attr-defined]
        tenant_id=TENANT_ID, document_id=document_id
    )


async def test_get_missing_document_raises(
    service: KnowledgeService, repository: KnowledgeDocumentRepository
) -> None:
    repository.get.return_value = None  # type: ignore[attr-defined]

    with pytest.raises(DocumentNotFoundError):
        await service.get(tenant_id=TENANT_ID, document_id=uuid.uuid4())


async def test_list_returns_page_and_total(
    service: KnowledgeService, repository: KnowledgeDocumentRepository
) -> None:
    items = [SimpleNamespace(id=uuid.uuid4())]
    repository.list_for_tenant.return_value = items  # type: ignore[attr-defined]
    repository.count_for_tenant.return_value = 41  # type: ignore[attr-defined]

    result, total = await service.list_documents(
        tenant_id=TENANT_ID, status=DocumentStatus.READY, limit=10, offset=20
    )

    assert (result, total) == (items, 41)
    repository.list_for_tenant.assert_awaited_once_with(  # type: ignore[attr-defined]
        tenant_id=TENANT_ID, status=DocumentStatus.READY, limit=10, offset=20
    )
    repository.count_for_tenant.assert_awaited_once_with(  # type: ignore[attr-defined]
        tenant_id=TENANT_ID, status=DocumentStatus.READY
    )


# --- delete -------------------------------------------------------------------------------


async def test_delete_removes_vectors_then_row_then_file(
    service: KnowledgeService, repository: KnowledgeDocumentRepository, events: Events, storage: FakeStorage
) -> None:
    document_id = uuid.uuid4()
    repository.get.return_value = SimpleNamespace(id=document_id, storage_key="t/d")  # type: ignore[attr-defined]

    await service.delete(tenant_id=TENANT_ID, document_id=document_id)

    assert events.log == ["delete_vectors", "delete_row", "commit", "delete_file"]
    assert storage.deleted == ["t/d"]


async def test_delete_missing_document_touches_nothing(
    service: KnowledgeService, repository: KnowledgeDocumentRepository, events: Events
) -> None:
    repository.get.return_value = None  # type: ignore[attr-defined]

    with pytest.raises(DocumentNotFoundError):
        await service.delete(tenant_id=TENANT_ID, document_id=uuid.uuid4())

    assert events.log == []