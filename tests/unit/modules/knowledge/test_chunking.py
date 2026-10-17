import pytest

from app.modules.knowledge.chunking import TextChunker
from app.modules.knowledge.extractors import ExtractedPage

SIZE = 100
OVERLAP = 20


def words(count: int) -> str:
    return " ".join(f"w{i:04d}" for i in range(count))  # unique 5-char words


@pytest.fixture
def chunker() -> TextChunker:
    return TextChunker(chunk_size=SIZE, chunk_overlap=OVERLAP)


@pytest.mark.parametrize(
    ("size", "overlap"),
    [(0, 0), (-5, 0), (100, -1), (100, 100), (100, 150)],
)
def test_invalid_configuration_is_rejected(size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        TextChunker(chunk_size=size, chunk_overlap=overlap)


@pytest.mark.parametrize("text", ["", "   ", "\n\n \t\n"])
def test_blank_text_produces_no_chunks(chunker: TextChunker, text: str) -> None:
    assert chunker.split_text(text) == []


def test_short_text_is_a_single_chunk(chunker: TextChunker) -> None:
    assert chunker.split_text("  3 bedroom villa in Marina  ") == ["3 bedroom villa in Marina"]


def test_chunks_never_exceed_chunk_size(chunker: TextChunker) -> None:
    chunks = chunker.split_text(words(300))

    assert len(chunks) > 1
    assert all(len(chunk) <= SIZE for chunk in chunks)


def test_no_content_is_lost(chunker: TextChunker) -> None:
    text = words(300)

    chunks = chunker.split_text(text)

    assert {w for chunk in chunks for w in chunk.split()} == set(text.split())


def test_consecutive_chunks_overlap(chunker: TextChunker) -> None:
    chunks = chunker.split_text(words(300))

    for previous, following in zip(chunks, chunks[1:], strict=False):
        assert following.split()[0] in previous.split()


def test_zero_overlap_produces_disjoint_chunks() -> None:
    chunker = TextChunker(chunk_size=SIZE, chunk_overlap=0)

    chunks = chunker.split_text(words(300))

    all_words = [w for chunk in chunks for w in chunk.split()]
    assert all_words == words(300).split()


def test_prefers_paragraph_boundaries() -> None:
    chunker = TextChunker(chunk_size=SIZE, chunk_overlap=0)
    first = " ".join(["alpha"] * 10)
    second = " ".join(["beta"] * 12)

    chunks = chunker.split_text(f"{first}\n\n{second}")

    assert chunks == [first, second]


def test_splits_on_line_boundaries_before_words() -> None:
    chunker = TextChunker(chunk_size=SIZE, chunk_overlap=0)
    lines = [f"Feature {i:02d}: " + "x" * 25 for i in range(10)]

    chunks = chunker.split_text("\n".join(lines))

    assert len(chunks) > 1
    assert all(line in lines for chunk in chunks for line in chunk.split("\n"))


def test_text_without_separators_is_hard_split_without_redundant_tail(
    chunker: TextChunker,
) -> None:
    text = "x" * 250  # step = 80 -> windows start at 0, 80, 160 and the last one reaches the end

    chunks = chunker.split_text(text)

    assert [len(chunk) for chunk in chunks] == [100, 100, 90]
    assert chunks[0][:80] + chunks[1][:80] + chunks[2] == text


def test_chunk_pages_assigns_page_numbers_and_global_index(chunker: TextChunker) -> None:
    pages = [
        ExtractedPage(number=1, text="first page"),
        ExtractedPage(number=3, text=" ".join(["word"] * 60)),
    ]

    chunks = chunker.chunk_pages(pages)

    assert chunks[0].page_number == 1
    assert all(chunk.page_number == 3 for chunk in chunks[1:])
    assert len(chunks) > 2
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))


def test_chunk_pages_with_no_pages_returns_empty(chunker: TextChunker) -> None:
    assert chunker.chunk_pages([]) == []