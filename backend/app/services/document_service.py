"""Document ingestion and management service.

Orchestrates the ingestion pipeline:
    validate -> hash -> dedupe -> extract -> chunk -> embed -> persist.
"""
from __future__ import annotations

import hashlib

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.embeddings import get_embedding_provider
from app.ingestion import ExtractionError, chunk_segments, extract
from app.models import Chunk, Document


class DuplicateDocumentError(Exception):
    """Raised when a document with the same content hash already exists."""

    def __init__(self, existing: Document):
        self.existing = existing
        super().__init__(f"Document already indexed (id={existing.id})")


def compute_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_upload(filename: str, data: bytes) -> str:
    """Validate extension and size. Returns the normalized file extension."""
    ext = file_extension(filename)
    if ext not in settings.allowed_extensions_set:
        raise ExtractionError(
            f"Unsupported extension '.{ext}'. Allowed: {sorted(settings.allowed_extensions_set)}"
        )
    if len(data) == 0:
        raise ExtractionError("Uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise ExtractionError(
            f"File exceeds max size of {settings.max_upload_mb} MB."
        )
    return ext


def ingest_document(db: Session, filename: str, data: bytes) -> tuple[Document, bool]:
    """Ingest a document end to end.

    Returns (document, duplicate). If a duplicate is found, the existing document
    is returned with duplicate=True and nothing new is written.
    """
    ext = validate_upload(filename, data)
    content_hash = compute_hash(data)

    existing = db.scalar(select(Document).where(Document.content_hash == content_hash))
    if existing is not None:
        return existing, True

    # extract -> chunk
    segments = extract(ext, data)
    raw_text = "\n\n".join(s.text for s in segments)
    chunks = chunk_segments(
        segments, chunk_size=settings.chunk_size, overlap=settings.chunk_overlap
    )
    if not chunks:
        raise ExtractionError("Document produced no chunks.")

    # embed
    embedder = get_embedding_provider()
    vectors = embedder.embed_batch([c.content for c in chunks])

    profile = settings.default_index_profile

    # persist
    document = Document(
        filename=filename,
        file_type=ext,
        content_hash=content_hash,
        size_bytes=len(data),
        chunk_count=len(chunks),
        status="indexed",
        raw_text=raw_text,
    )
    db.add(document)
    db.flush()  # assigns document.id

    for c, vec in zip(chunks, vectors, strict=True):
        db.add(
            Chunk(
                document_id=document.id,
                index_profile=profile,
                chunk_index=c.index,
                section=c.section,
                page=c.page,
                content=c.content,
                embedding=vec,
            )
        )
    db.commit()
    db.refresh(document)
    return document, False


def list_documents(db: Session) -> list[Document]:
    return list(db.scalars(select(Document).order_by(Document.created_at.desc())))


def get_document(db: Session, document_id: int) -> Document | None:
    return db.get(Document, document_id)


def delete_document(db: Session, document_id: int) -> bool:
    """Delete a document and its chunks (cascade). Returns True if deleted."""
    doc = db.get(Document, document_id)
    if doc is None:
        return False
    db.delete(doc)  # cascade removes chunks
    db.commit()
    return True


def stats(db: Session) -> dict:
    total_docs = db.scalar(select(func.count(Document.id))) or 0
    total_chunks = db.scalar(select(func.count(Chunk.id))) or 0
    rows = db.execute(
        select(Document.file_type, func.count(Document.id)).group_by(Document.file_type)
    ).all()
    file_types = {ft: n for ft, n in rows}
    recent = list(
        db.scalars(select(Document).order_by(Document.created_at.desc()).limit(5))
    )
    return {
        "documents": total_docs,
        "chunks": total_chunks,
        "file_types": file_types,
        "recent": recent,
    }
