import re
import unicodedata

# Control characters except \t and \n (\r is converted to \n before this runs)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_HORIZONTAL_SPACE = re.compile(r"[^\S\n]+")
_SPACE_AROUND_NEWLINE = re.compile(r" ?\n ?")
_BLANK_LINES = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    """Make extracted text safe and consistent for chunking and embedding.

    - NFKC folds PDF ligatures ("ﬁ" -> "fi") and non-breaking spaces.
    - Null/control characters are removed (they break JSON payloads and Postgres text).
    - Whitespace is collapsed while paragraph breaks are preserved.
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS.sub("", text)
    text = _HORIZONTAL_SPACE.sub(" ", text)
    text = _SPACE_AROUND_NEWLINE.sub("\n", text)
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip()