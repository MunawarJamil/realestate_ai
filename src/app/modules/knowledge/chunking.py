from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from app.modules.knowledge.extractors import ExtractedPage

# Tried in order: paragraph -> line -> word. Anything longer falls back to a hard split.
_SEPARATORS: Final[tuple[str, ...]] = ("\n\n", "\n", " ")


@dataclass(frozen=True, slots=True)
class TextChunk:
    index: int  # position within the whole document, 0-based
    text: str
    page_number: int


class TextChunker:
    """Recursive splitter that prefers natural boundaries and keeps a bounded overlap.

    Sizes are in characters, so the chunker has no tokenizer dependency and behaves the same
    for every embedding provider. Every chunk is guaranteed to be <= chunk_size.
    """

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")
        if not 0 <= chunk_overlap < chunk_size:
            raise ValueError("chunk_overlap must be >= 0 and smaller than chunk_size.")
        self._chunk_size = chunk_size
        self._overlap = chunk_overlap

    def chunk_pages(self, pages: Sequence[ExtractedPage]) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        for page in pages:
            for text in self.split_text(page.text):
                chunks.append(TextChunk(index=len(chunks), text=text, page_number=page.number))
        return chunks

    def split_text(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        return [chunk for chunk in (c.strip() for c in self._split(text, _SEPARATORS)) if chunk]

    def _split(self, text: str, separators: Sequence[str]) -> list[str]:
        if len(text) <= self._chunk_size:
            return [text]

        separator = next((s for s in separators if s in text), None)
        if separator is None:
            return self._hard_split(text)
        remaining = separators[separators.index(separator) + 1 :]

        chunks: list[str] = []
        buffer: list[str] = []  # consecutive pieces small enough to be merged together
        for raw_piece in text.split(separator):
            piece = raw_piece.strip()
            if not piece:
                continue
            if len(piece) <= self._chunk_size:
                buffer.append(piece)
                continue
            if buffer:
                chunks.extend(self._merge(buffer, separator))
                buffer = []
            chunks.extend(self._split(piece, remaining))
        if buffer:
            chunks.extend(self._merge(buffer, separator))
        return chunks

    def _merge(self, pieces: Sequence[str], separator: str) -> list[str]:
        """Greedily pack pieces into chunks, carrying a tail of <= overlap chars forward."""
        sep_len = len(separator)
        chunks: list[str] = []
        window: deque[str] = deque()
        total = 0

        for piece in pieces:
            if window and total + sep_len + len(piece) > self._chunk_size:
                chunks.append(separator.join(window))
                while window and (
                    total > self._overlap or total + sep_len + len(piece) > self._chunk_size
                ):
                    removed = window.popleft()
                    total -= len(removed) + (sep_len if window else 0)
            total += len(piece) + (sep_len if window else 0)
            window.append(piece)

        if window:
            chunks.append(separator.join(window))
        return chunks

    def _hard_split(self, text: str) -> list[str]:
        """Fixed windows for text with no usable separator (e.g. one huge token)."""
        step = self._chunk_size - self._overlap
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + self._chunk_size
            chunks.append(text[start:end])
            if end >= len(text):
                break
            start += step
        return chunks