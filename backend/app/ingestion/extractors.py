"""Text extraction for supported formats: PDF, DOCX, MD, TXT.

Each extractor returns a list of (text, page) tuples. `page` is populated for
PDFs and left as None for flow formats. No heavy OCR is performed in V1: a PDF
with no extractable text raises ExtractionError.
"""
from __future__ import annotations

import io

from pypdf import PdfReader

from app.ingestion.chunking import Segment


class ExtractionError(ValueError):
    """Raised when a file has no extractable text or the format is unsupported."""


def _extract_pdf(data: bytes) -> list[Segment]:
    reader = PdfReader(io.BytesIO(data))
    segments: list[Segment] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            segments.append(Segment(text=text, page=i, section=None))
    if not segments:
        raise ExtractionError(
            "No extractable text found in PDF (scanned/image-only PDFs are not supported in V1)."
        )
    return segments


def _extract_docx(data: bytes) -> list[Segment]:
    from docx import Document as DocxDocument

    doc = DocxDocument(io.BytesIO(data))
    segments: list[Segment] = []
    current_section: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            text = "\n".join(buffer).strip()
            if text:
                segments.append(Segment(text=text, page=None, section=current_section))
            buffer.clear()

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        if (para.style and para.style.name or "").lower().startswith("heading"):
            flush()
            current_section = text
        buffer.append(text)
    flush()

    if not segments:
        raise ExtractionError("No extractable text found in DOCX.")
    return segments


def _extract_markdown(data: bytes) -> list[Segment]:
    text = data.decode("utf-8", errors="replace")
    segments: list[Segment] = []
    current_section: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            joined = "\n".join(buffer).strip()
            if joined:
                segments.append(Segment(text=joined, page=None, section=current_section))
            buffer.clear()

    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            flush()
            current_section = line.lstrip("#").strip()
        buffer.append(line)
    flush()

    if not segments:
        raise ExtractionError("No extractable text found in Markdown file.")
    return segments


def _extract_txt(data: bytes) -> list[Segment]:
    text = data.decode("utf-8", errors="replace").strip()
    if not text:
        raise ExtractionError("No extractable text found in TXT file.")
    return [Segment(text=text, page=None, section=None)]


_EXTRACTORS = {
    "pdf": _extract_pdf,
    "docx": _extract_docx,
    "md": _extract_markdown,
    "txt": _extract_txt,
}


def extract(file_type: str, data: bytes) -> list[Segment]:
    """Extract text segments for a given file type."""
    fn = _EXTRACTORS.get(file_type.lower())
    if fn is None:
        raise ExtractionError(f"Unsupported file type: {file_type}")
    return fn(data)
