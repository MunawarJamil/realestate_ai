from pathlib import PurePosixPath
from typing import Final

from app.modules.knowledge.exceptions import InvalidDocumentError, UnsupportedContentTypeError
from app.modules.knowledge.extractors import is_supported_content_type

_EXTENSION_TYPES: Final = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}
_MAX_FILENAME_LENGTH: Final = 255
_PDF_SIGNATURE: Final = b"%PDF-"
_SNIFF_BYTES: Final = 1024


def sanitize_filename(filename: str | None) -> str:
    """Display-only name: no directories, no control characters, bounded length."""
    name = PurePosixPath((filename or "").replace("\\", "/")).name
    name = "".join(ch for ch in name if ch.isprintable()).strip()[:_MAX_FILENAME_LENGTH]
    return name or "untitled"


def resolve_content_type(filename: str, declared: str | None) -> str:
    """The extension wins: browsers often send application/octet-stream for .md files."""
    resolved = _EXTENSION_TYPES.get(PurePosixPath(filename).suffix.lower())
    if resolved is not None:
        return resolved
    if declared and is_supported_content_type(declared):
        return declared.split(";", 1)[0].strip().lower()
    raise UnsupportedContentTypeError(declared or "unknown")


def ensure_content_matches_type(content_type: str, data: bytes) -> None:
    """Cheap sanity check so an obviously wrong file fails at upload, not later in the worker."""
    head = data[:_SNIFF_BYTES]
    if content_type == "application/pdf":
        if _PDF_SIGNATURE not in head:
            raise InvalidDocumentError("The file is not a valid PDF.")
    elif b"\x00" in head:
        raise InvalidDocumentError("The file is not a text document.")