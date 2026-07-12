from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(slots=True)
class ChunkRecord:
    text: str
    source_file: str
    doc_id: str
    page: int | None
    chunk_id: str
    source_type: str


def _window_words(words: list[str], chunk_size: int, overlap: int) -> Iterable[tuple[int, list[str]]]:
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        yield start, words[start:end]
        if end >= len(words):
            break
        start = max(0, end - overlap)


def chunk_text(
    text: str,
    *,
    source_file: str,
    doc_id: str,
    page: int | None,
    source_type: str,
    chunk_size_words: int = 220,
    overlap_words: int = 40,
) -> list[ChunkRecord]:
    """Split text into overlapping chunks while preserving source metadata."""

    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    words = cleaned.split(" ")
    records: list[ChunkRecord] = []
    for index, (start, window) in enumerate(_window_words(words, chunk_size_words, overlap_words), start=1):
        chunk_text_value = " ".join(window).strip()
        if not chunk_text_value:
            continue
        page_tag = f"p{page}" if page is not None and page > 0 else "nopage"
        chunk_id = f"{doc_id}::{page_tag}::chunk{index}"
        records.append(
            ChunkRecord(
                text=chunk_text_value,
                source_file=source_file,
                doc_id=doc_id,
                page=page,
                chunk_id=chunk_id,
                source_type=source_type,
            )
        )
    return records
