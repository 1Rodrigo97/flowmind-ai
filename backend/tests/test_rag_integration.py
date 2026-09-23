"""Full-stack integration tests (Postgres + pgvector + Ollama).

These skip automatically when the stack is not available. They cover:
    T4 duplicate detection, T5 chunks persisted, T6 embeddings persisted,
    T7 semantic search relevance, T8 chat with source, T9 insufficient-context
    no hallucination, T10 delete removes chunks, plus the ingest->retrieve->
    answer->sources integration path.
"""
from __future__ import annotations

from sqlalchemy import func, select

from app.models import Chunk
from app.rag import chat, search
from app.services import document_service as svc
from tests.conftest import requires_stack

RAG_DOC = (
    b"# RAG\n\nRetrieval-Augmented Generation retrieves context from a knowledge "
    b"base and grounds the answer on that retrieved context to reduce hallucination."
)
FT_DOC = (
    b"# Fine-tuning\n\nFine-tuning updates the weights of the model on a "
    b"task-specific dataset to change its style and behavior."
)


@requires_stack
def test_ingest_persists_chunks_and_embeddings(db):
    """T5 + T6: chunks and their embeddings are persisted."""
    doc, dup = svc.ingest_document(db, "rag.md", RAG_DOC)
    assert not dup
    assert doc.chunk_count >= 1

    n = db.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == doc.id))
    assert n == doc.chunk_count
    chunk = db.scalar(select(Chunk).where(Chunk.document_id == doc.id))
    assert chunk.embedding is not None
    assert len(list(chunk.embedding)) == 768


@requires_stack
def test_duplicate_document_detected(db):
    """T4: same content is not indexed twice."""
    doc1, dup1 = svc.ingest_document(db, "rag.md", RAG_DOC)
    doc2, dup2 = svc.ingest_document(db, "rag-copy.md", RAG_DOC)
    assert dup1 is False
    assert dup2 is True
    assert doc1.id == doc2.id


@requires_stack
def test_semantic_search_returns_relevant_document(db):
    """T7: retrieval ranks the relevant document first."""
    svc.ingest_document(db, "rag.md", RAG_DOC)
    svc.ingest_document(db, "fine_tuning.md", FT_DOC)
    results = search(db, "What is retrieval augmented generation?", top_k=3)["results"]
    assert results
    assert results[0]["document"] == "rag.md"
    assert results[0]["score"] > 0


@requires_stack
def test_chat_answers_with_sources(db):
    """T8: a grounded answer comes back with at least one source."""
    svc.ingest_document(db, "rag.md", RAG_DOC)
    result = chat(db, "What does RAG do to reduce hallucination?", top_k=3)
    assert result["status"] == "answered"
    assert result["sources"]
    assert result["sources"][0]["document"] == "rag.md"


@requires_stack
def test_insufficient_context_does_not_hallucinate(db):
    """T9: an unrelated question over the corpus returns insufficient context."""
    svc.ingest_document(db, "rag.md", RAG_DOC)
    result = chat(db, "What time does the pharmacy in Lisbon close on Sundays?", top_k=3)
    assert result["status"] == "insufficient_context"
    assert result["sources"] == []


@requires_stack
def test_delete_removes_chunks(db):
    """T10: deleting a document cascades to its chunks."""
    doc, _ = svc.ingest_document(db, "rag.md", RAG_DOC)
    assert db.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == doc.id)) > 0
    assert svc.delete_document(db, doc.id) is True
    assert db.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == doc.id)) == 0
