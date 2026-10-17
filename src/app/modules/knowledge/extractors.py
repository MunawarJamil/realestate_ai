import asyncio
import io
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Protocol

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.modules.knowledge.exceptions import (
    EmptyDocumentError,
    ExtractionError,
    UnsupportedContentTypeError,
)
from app.modules.knowledge.text import normalize_text


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    number: int  # 1-based
    text: str


class TextExtractor(Protocol):
    """Synchronous and CPU-bound; callers must run it off the event loop."""

    def extract(self, data: bytes) -> list[ExtractedPage]: ...


class PlainTextExtractor:
    def extract(self, data: bytes) -> list[ExtractedPage]:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ExtractionError("File is not valid UTF-8 text.") from exc
        return [ExtractedPage(number=1, text=text)]


class PdfExtractor:
    def extract(self, data: bytes) -> list[ExtractedPage]:
        try:
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise ExtractionError("Encrypted PDFs are not supported.")
            return [
                ExtractedPage(number=index, text=page.extract_text() or "")
                for index, page in enumerate(reader.pages, start=1)
            ]
        except ExtractionError:
            raise
        except (PyPdfError, ValueError, KeyError, TypeError, RecursionError) as exc:
            # pypdf surfaces malformed input as many different exception types
            raise ExtractionError("PDF could not be read.") from exc


_EXTRACTORS: Final[Mapping[str, TextExtractor]] = {
    "application/pdf": PdfExtractor(),
    "text/plain": PlainTextExtractor(),
    "text/markdown": PlainTextExtractor(),
}


def _base_content_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


def is_supported_content_type(content_type: str) -> bool:
    return _base_content_type(content_type) in _EXTRACTORS


async def extract_pages(content_type: str, data: bytes) -> list[ExtractedPage]:
    """Extract cleaned, non-empty pages. Original page numbers are preserved."""
    extractor = _EXTRACTORS.get(_base_content_type(content_type))
    if extractor is None:
        raise UnsupportedContentTypeError(content_type)

    # PDF parsing is CPU-bound; keep it off the event loop.
    raw_pages = await asyncio.to_thread(extractor.extract, data)

    pages = [
        ExtractedPage(number=page.number, text=normalize_text(page.text)) for page in raw_pages
    ]
    pages = [page for page in pages if page.text]
    if not pages:
        raise EmptyDocumentError(
            "Document contains no extractable text. Scanned files need OCR, which is not supported."
        )
    return pages