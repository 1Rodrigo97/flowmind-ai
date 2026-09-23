"""Index-profile management: (re)indexing the corpus under a given profile.

Changing the embedding model, chunk size or overlap requires re-embedding the
corpus into a new profile. Chunks are tagged with the profile so retrieval never
mixes incompatible embeddings. Reindexing uses each document's stored raw_text, so
the original uploaded file is not needed.
"""
from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.embeddings import get_embedding_provider
from app.ingestion.chunking import Segment, chunk_segments
from app.models import Chunk, Document


def profile_chunk_count(db: Session, profile: str) -> int:
    return db.scalar(select(func.count(Chunk.id)).where(Chunk.index_profile == profile)) or 0


def ensure_profile(
    db: Session,
    profile: str,
    chunk_size: int,
    chunk_overlap: int,
    *,
    force: bool = False,
) -> int:
    """Ensure chunks for ``profile`` exist, reindexing the corpus if needed.

    Returns the number of chunks available under the profile.
    """
    existing = profile_chunk_count(db, profile)
    if existing > 0 and not force:
        return existing

    if force:
        db.execute(delete(Chunk).where(Chunk.index_profile == profile))
        db.flush()

    embedder = get_embedding_provider()
    documents = list(db.scalars(select(Document).where(Document.raw_text.is_not(None))))

    total = 0
    for doc in documents:
        chunks = chunk_segments(
            [Segment(text=doc.raw_text or "")],
            chunk_size=chunk_size,
            overlap=chunk_overlap,
        )
        if not chunks:
            continue
        vectors = embedder.embed_batch([c.content for c in chunks])
        for c, vec in zip(chunks, vectors, strict=True):
            db.add(
                Chunk(
                    document_id=doc.id,
                    index_profile=profile,
                    chunk_index=c.index,
                    section=c.section,
                    page=c.page,
                    content=c.content,
                    embedding=vec,
                )
            )
        total += len(chunks)

    db.commit()
    return total
