from collections.abc import Callable, Sequence

import pytest

from app.modules.knowledge import extractors
from app.modules.knowledge.exceptions import (
    EmptyDocumentError,
    ExtractionError,
    UnsupportedContentTypeError,
)
from app.modules.knowledge.extractors import (
    ExtractedPage,
    PdfExtractor,
    PlainTextExtractor,
    extract_pages,
    is_supported_content_type,
)


class FakePage:
    def __init__(self, text: str | None) -> None:
        self._text = text

    def extract_text(self) -> str | None:
        return self._text


class FakeReader:
    def __init__(self, pages: Sequence[FakePage], *, encrypted: bool = False) -> None:
        self.pages = list(pages)
        self.is_encrypted = encrypted


def use_fake_reader(monkeypatch: pytest.MonkeyPatch, reader: FakeReader) -> None:
    factory: Callable[[object], FakeReader] = lambda stream: reader  # noqa: E731
    monkeypatch.setattr(extractors, "PdfReader", factory)


# --- PlainTextExtractor -------------------------------------------------------------------


def test_plain_text_decodes_utf8() -> None:
    pages = PlainTextExtractor().extract("Dubai Marina".encode())

    assert pages == [ExtractedPage(number=1, text="Dubai Marina")]


def test_plain_text_strips_utf8_bom() -> None:
    pages = PlainTextExtractor().extract(b"\xef\xbb\xbfhello")

    assert pages[0].text == "hello"


def test_plain_text_rejects_invalid_utf8() -> None:
    with pytest.raises(ExtractionError):
        PlainTextExtractor().extract(b"\xff\xfe\x00broken\x80")


# --- PdfExtractor -------------------------------------------------------------------------


def test_pdf_pages_are_numbered_from_one_and_none_becomes_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_fake_reader(monkeypatch, FakeReader([FakePage("first"), FakePage(None)]))

    pages = PdfExtractor().extract(b"%PDF")

    assert pages == [ExtractedPage(1, "first"), ExtractedPage(2, "")]


def test_pdf_encrypted_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    use_fake_reader(monkeypatch, FakeReader([FakePage("secret")], encrypted=True))

    with pytest.raises(ExtractionError, match="Encrypted"):
        PdfExtractor().extract(b"%PDF")


def test_pdf_garbage_bytes_raise_extraction_error() -> None:
    with pytest.raises(ExtractionError):
        PdfExtractor().extract(b"this is definitely not a pdf")


# --- extract_pages ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content_type",
    ["text/plain", "text/markdown", "TEXT/PLAIN; charset=utf-8", "application/pdf"],
)
def test_supported_content_types(content_type: str) -> None:
    assert is_supported_content_type(content_type)


def test_unsupported_content_type_is_not_supported() -> None:
    assert not is_supported_content_type("image/png")


async def test_extract_pages_rejects_unsupported_type() -> None:
    with pytest.raises(UnsupportedContentTypeError) as exc_info:
        await extract_pages("image/png", b"data")

    assert exc_info.value.content_type == "image/png"


async def test_extract_pages_accepts_content_type_with_charset() -> None:
    pages = await extract_pages("text/plain; charset=utf-8", b"hello")

    assert pages == [ExtractedPage(1, "hello")]


async def test_extract_pages_normalizes_text() -> None:
    pages = await extract_pages("text/plain", b"a   b\r\n\r\n\r\n\r\nc")

    assert pages[0].text == "a b\n\nc"


async def test_extract_pages_drops_blank_pages_but_keeps_original_numbers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_fake_reader(
        monkeypatch,
        FakeReader([FakePage("one"), FakePage("   "), FakePage(None), FakePage("four")]),
    )

    pages = await extract_pages("application/pdf", b"%PDF")

    assert [(p.number, p.text) for p in pages] == [(1, "one"), (4, "four")]


@pytest.mark.parametrize("payload", [b"", b"   \n\t  "])
async def test_extract_pages_raises_when_no_text(payload: bytes) -> None:
    with pytest.raises(EmptyDocumentError):
        await extract_pages("text/plain", payload)


async def test_scanned_pdf_without_text_layer_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    use_fake_reader(monkeypatch, FakeReader([FakePage(None), FakePage("")]))

    with pytest.raises(EmptyDocumentError, match="OCR"):
        await extract_pages("application/pdf", b"%PDF")