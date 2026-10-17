import pytest

from app.modules.knowledge.text import normalize_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("a\r\nb", "a\nb"),
        ("a\rb", "a\nb"),
        ("a\x00b", "ab"),
        ("a   \t b", "a b"),
        ("a\u00a0b", "a b"),
        ("a\n\n\n\nb", "a\n\nb"),
        ("  a \n b  ", "a\nb"),
        ("ﬁnal", "final"),
        ("   \n\t ", ""),
    ],
)
def test_normalize_text(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


def test_normalize_text_is_idempotent() -> None:
    raw = "Villa  \r\n\r\n\r\n 3 BR\x00 ﬁnished"
    once = normalize_text(raw)

    assert normalize_text(once) == once


def test_normalize_text_preserves_arabic_and_paragraph_breaks() -> None:
    raw = "شقة في دبي\n\nغرفتين نوم"

    assert normalize_text(raw) == raw