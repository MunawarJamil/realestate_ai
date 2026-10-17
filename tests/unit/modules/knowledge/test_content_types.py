import pytest

from app.modules.knowledge.content_types import (
    ensure_content_matches_type,
    resolve_content_type,
    sanitize_filename,
)
from app.modules.knowledge.exceptions import InvalidDocumentError, UnsupportedContentTypeError


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("brochure.pdf", "brochure.pdf"),
        ("../../etc/passwd", "passwd"),
        ("C:\\Users\\me\\listing.txt", "listing.txt"),
        ("bad\x00na\nme.md", "badname.md"),
        ("   ", "untitled"),
        ("", "untitled"),
        (None, "untitled"),
    ],
)
def test_sanitize_filename(raw: str | None, expected: str) -> None:
    assert sanitize_filename(raw) == expected


def test_sanitize_filename_truncates_long_names() -> None:
    assert len(sanitize_filename("a" * 500 + ".pdf")) == 255


@pytest.mark.parametrize(
    ("filename", "declared", "expected"),
    [
        ("a.pdf", None, "application/pdf"),
        ("A.PDF", "application/octet-stream", "application/pdf"),
        ("notes.md", "application/octet-stream", "text/markdown"),
        ("notes.markdown", None, "text/markdown"),
        ("listing.txt", "application/pdf", "text/plain"),  # extension wins
        ("noextension", "text/plain; charset=utf-8", "text/plain"),
    ],
)
def test_resolve_content_type(filename: str, declared: str | None, expected: str) -> None:
    assert resolve_content_type(filename, declared) == expected


@pytest.mark.parametrize(
    ("filename", "declared"),
    [("photo.png", "image/png"), ("noextension", None), ("data.bin", "application/octet-stream")],
)
def test_resolve_content_type_rejects_unsupported(filename: str, declared: str | None) -> None:
    with pytest.raises(UnsupportedContentTypeError):
        resolve_content_type(filename, declared)


def test_pdf_signature_is_accepted() -> None:
    ensure_content_matches_type("application/pdf", b"%PDF-1.7\n...")


def test_pdf_signature_may_follow_leading_bytes() -> None:
    ensure_content_matches_type("application/pdf", b"\xef\xbb\xbf  %PDF-1.4\n")


def test_pdf_without_signature_is_rejected() -> None:
    with pytest.raises(InvalidDocumentError, match="PDF"):
        ensure_content_matches_type("application/pdf", b"just some text")


@pytest.mark.parametrize("content_type", ["text/plain", "text/markdown"])
def test_binary_data_is_rejected_for_text_types(content_type: str) -> None:
    with pytest.raises(InvalidDocumentError, match="text"):
        ensure_content_matches_type(content_type, b"abc\x00\x01binary")


def test_plain_text_is_accepted() -> None:
    ensure_content_matches_type("text/plain", "Villa in Dubai".encode())