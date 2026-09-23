"""Pure unit tests for extraction, chunking, hashing and validation.

Covers T1/T2/T3 (extraction per format), T12 (invalid file rejected) and the
chunking contract -- all without a database or Ollama.
"""
from __future__ import annotations

import io

import pytest
from docx import Document as DocxDocument
from pypdf import PdfWriter
from tests.reportlab_stub import make_text_pdf  # local helper below

from app.ingestion import chunk_segments, extract
from app.ingestion.extractors import ExtractionError
from app.services.document_service import compute_hash, file_extension, validate_upload


def test_extract_markdown_keeps_sections():
    md = b"# Title\n\nIntro paragraph.\n\n## Details\n\nMore text here."
    segs = extract("md", md)
    assert any(s.section == "Title" for s in segs)
    assert any(s.section == "Details" for s in segs)


def test_extract_txt():
    segs = extract("txt", b"just some plain text")
    assert segs[0].text == "just some plain text"
    assert segs[0].page is None


def test_extract_docx(tmp_path):
    doc = DocxDocument()
    doc.add_heading("Section A", level=1)
    doc.add_paragraph("Body of section A with content.")
    buf = io.BytesIO()
    doc.save(buf)
    segs = extract("docx", buf.getvalue())
    assert any("section a" in s.text.lower() for s in segs)


def test_extract_pdf_textual():
    data = make_text_pdf("Hello RAG world on a PDF page.")
    segs = extract("pdf", data)
    assert segs[0].page == 1
    assert "RAG" in segs[0].text


def test_extract_pdf_without_text_raises():
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    with pytest.raises(ExtractionError):
        extract("pdf", buf.getvalue())


def test_unsupported_extension_rejected():
    with pytest.raises(ExtractionError):
        validate_upload("malware.exe", b"data")


def test_empty_file_rejected():
    with pytest.raises(ExtractionError):
        validate_upload("notes.md", b"")


def test_chunking_overlap_and_indices():
    words = " ".join(str(i) for i in range(100))
    from app.ingestion.chunking import Segment

    chunks = chunk_segments([Segment(text=words)], chunk_size=30, overlap=10)
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert len(chunks) >= 4  # 100 words, step 20
    # overlap: second chunk should share words with the first
    first_words = set(chunks[0].content.split())
    second_words = set(chunks[1].content.split())
    assert first_words & second_words


def test_chunk_metadata_preserved():
    from app.ingestion.chunking import Segment

    chunks = chunk_segments(
        [Segment(text="alpha beta gamma", page=7, section="Intro")],
        chunk_size=5,
        overlap=1,
    )
    assert chunks[0].page == 7
    assert chunks[0].section == "Intro"


def test_hash_and_extension():
    assert file_extension("Report.PDF") == "pdf"
    assert compute_hash(b"abc") == compute_hash(b"abc")
    assert compute_hash(b"abc") != compute_hash(b"abd")
