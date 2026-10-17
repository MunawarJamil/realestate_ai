import asyncio
import os
import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings
from app.modules.knowledge.exceptions import StorageFileNotFoundError


def build_storage_key(tenant_id: uuid.UUID, document_id: uuid.UUID) -> str:
    """Storage key is derived from ids only; user-supplied filenames never touch the filesystem."""
    return f"{tenant_id}/{document_id}"


class FileStorage(Protocol):
    async def save(self, *, key: str, data: bytes) -> None: ...

    async def read(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...


class LocalFileStorage:
    """Local-disk storage. Writes are atomic (temp file + rename) and keys cannot escape base_dir."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir.resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, *, key: str, data: bytes) -> None:
        path = self._resolve(key)
        await asyncio.to_thread(self._write_atomic, path, data)

    async def read(self, key: str) -> bytes:
        path = self._resolve(key)
        try:
            return await asyncio.to_thread(path.read_bytes)
        except FileNotFoundError as exc:
            raise StorageFileNotFoundError(key) from exc

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        await asyncio.to_thread(path.unlink, missing_ok=True)

    def _resolve(self, key: str) -> Path:
        path = (self._base_dir / key).resolve()
        if not key or path == self._base_dir or not path.is_relative_to(self._base_dir):
            raise ValueError(f"Invalid storage key: {key!r}")
        return path

    @staticmethod
    def _write_atomic(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temp_path.write_bytes(data)
            os.replace(temp_path, path)
        except BaseException:
            temp_path.unlink(missing_ok=True)
            raise


def build_file_storage() -> FileStorage:
    return LocalFileStorage(get_settings().storage_local_dir)