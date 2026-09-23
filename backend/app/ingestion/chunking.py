"""Segment model and word-based chunking with overlap.

Chunking preserves the metadata needed for grounded citation: section titles and
page numbers flow from the source segments into each chunk.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Segment:
    """A block of extracted text with optional source metadata."""

    text: str
    page: int | None = None
    section: str | None = None


@dataclass
class Chunk:
    """A retrieval unit ready for embedding."""

    index: int
    content: str
    page: int | None = None
    section: str | None = None


def chunk_segments(
    segments: list[Segment], chunk_size: int = 900, overlap: int = 150
) -> list[Chunk]:
    """Split segments into overlapping word-based chunks.

    Chunk/overlap are measured in words to stay tokenizer-agnostic. Each segment
    is chunked independently so page/section metadata is never mixed across
    boundaries.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    overlap = max(0, min(overlap, chunk_size - 1))
    step = chunk_size - overlap

    chunks: list[Chunk] = []
    idx = 0
    for seg in segments:
        words = seg.text.split()
        if not words:
            continue
        start = 0
        while start < len(words):
            piece = " ".join(words[start : start + chunk_size]).strip()
            if piece:
                chunks.append(
                    Chunk(index=idx, content=piece, page=seg.page, section=seg.section)
                )
                idx += 1
            start += step
    return chunks
