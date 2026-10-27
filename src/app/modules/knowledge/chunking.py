"""Token-aware recursive text chunker."""

from collections.abc import Sequence
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.modules.knowledge.extractors import ExtractedPage


@dataclass(frozen=True, slots=True)
class TextChunk:
    index: int  # position within the whole document, 0-based
    text: str
    page_number: int


class TextChunker:
    """
    Supports natural real-estate document boundaries (paragraphs, tables, lists, sentences)
    and optional token-aware length calculation.
    """

    def __init__(
        self,
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")
        if not 0 <= chunk_overlap < chunk_size:
            raise ValueError("chunk_overlap must be >= 0 and smaller than chunk_size.")

        self._chunk_size = chunk_size
        self._overlap = chunk_overlap

        # Standard hierarchy: paragraphs -> table/markdown lines -> sentences -> words -> chars
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True,
            strip_whitespace=True,
        )

    def chunk_pages(self, pages: Sequence[ExtractedPage]) -> list[TextChunk]:
        """Split extracted document pages into indexed TextChunk objects."""
        chunks: list[TextChunk] = []
        for page in pages:
            for text in self.split_text(page.text):
                chunks.append(TextChunk(index=len(chunks), text=text, page_number=page.number))
        return chunks

    def split_text(self, text: str) -> list[str]:
        """Splits raw text into non-empty chunks adhering to chunk_size and chunk_overlap."""
        clean = text.strip()
        if not clean:
            return []
        return [chunk for chunk in self._splitter.split_text(clean) if chunk.strip()]
