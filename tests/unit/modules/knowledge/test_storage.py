import uuid
from pathlib import Path

import pytest

from app.modules.knowledge import storage as storage_module
from app.modules.knowledge.exceptions import StorageFileNotFoundError
from app.modules.knowledge.storage import LocalFileStorage, build_storage_key


@pytest.fixture
def base_dir(tmp_path: Path) -> Path:
    return tmp_path / "uploads"


@pytest.fixture
def storage(base_dir: Path) -> LocalFileStorage:
    return LocalFileStorage(base_dir)


def test_build_storage_key_uses_only_ids() -> None:
    tenant_id, document_id = uuid.uuid4(), uuid.uuid4()

    assert build_storage_key(tenant_id, document_id) == f"{tenant_id}/{document_id}"


async def test_save_then_read_roundtrip(storage: LocalFileStorage) -> None:
    await storage.save(key="t1/d1", data=b"hello")

    assert await storage.read("t1/d1") == b"hello"


async def test_save_creates_nested_directories(
    storage: LocalFileStorage, base_dir: Path
) -> None:
    await storage.save(key="tenant/doc", data=b"x")

    assert (base_dir / "tenant" / "doc").read_bytes() == b"x"


async def test_save_overwrites_existing_content(storage: LocalFileStorage) -> None:
    await storage.save(key="t/d", data=b"old")
    await storage.save(key="t/d", data=b"new")

    assert await storage.read("t/d") == b"new"


async def test_save_leaves_no_temp_files(storage: LocalFileStorage, base_dir: Path) -> None:
    await storage.save(key="t/d", data=b"payload")

    assert list(base_dir.rglob("*.tmp")) == []


async def test_failed_write_cleans_up_temp_file_and_keeps_original(
    storage: LocalFileStorage, base_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    await storage.save(key="t/d", data=b"original")

    def broken_replace(src: object, dst: object) -> None:
        raise OSError("disk error")

    monkeypatch.setattr(storage_module.os, "replace", broken_replace)

    with pytest.raises(OSError, match="disk error"):
        await storage.save(key="t/d", data=b"replacement")

    monkeypatch.undo()
    assert list(base_dir.rglob("*.tmp")) == []
    assert await storage.read("t/d") == b"original"


async def test_read_missing_file_raises(storage: LocalFileStorage) -> None:
    with pytest.raises(StorageFileNotFoundError) as exc_info:
        await storage.read("t/missing")

    assert exc_info.value.key == "t/missing"


async def test_delete_removes_file(storage: LocalFileStorage) -> None:
    await storage.save(key="t/d", data=b"x")

    await storage.delete("t/d")

    with pytest.raises(StorageFileNotFoundError):
        await storage.read("t/d")


async def test_delete_missing_file_is_a_noop(storage: LocalFileStorage) -> None:
    await storage.delete("t/never-existed")


@pytest.mark.parametrize("key", ["", ".", "../escape", "a/../../escape", "/etc/passwd"])
async def test_keys_cannot_escape_base_directory(storage: LocalFileStorage, key: str) -> None:
    with pytest.raises(ValueError, match="Invalid storage key"):
        await storage.save(key=key, data=b"x")
    with pytest.raises(ValueError, match="Invalid storage key"):
        await storage.read(key)
    with pytest.raises(ValueError, match="Invalid storage key"):
        await storage.delete(key)