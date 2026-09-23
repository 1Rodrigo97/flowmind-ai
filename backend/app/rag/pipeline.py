"""RAG pipeline: retrieval and grounded chat.

Retrieval uses pgvector cosine distance. Grounding enforces that the LLM answers
only from retrieved context; when no chunk clears the similarity threshold, the
LLM is never asked to fabricate an answer -- INSUFFICIENT_CONTEXT is returned.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import log_event, new_request_id, timed
from app.embeddings import get_embedding_provider
from app.llm import get_llm_provider
from app.models import Chunk, Document

INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"

SYSTEM_PROMPT = (
    "You are FlowMind AI, a grounded knowledge assistant. Answer using ONLY the "
    "information present in the retrieved context below. If the context does not "
    "contain enough information to answer, reply exactly with "
    f"'{INSUFFICIENT_CONTEXT}'. Do not use prior knowledge and do not invent facts. "
    "Cite the sources you used by their document name."
)


def _retrieve(db: Session, query: str, top_k: int) -> list[dict]:
    """Return the top_k chunks by cosine similarity, with metadata and scores."""
    embedder = get_embedding_provider()
    query_vec = embedder.embed(query)

    # cosine_distance in [0, 2]; similarity = 1 - distance -> [-1, 1], ~[0,1] typically.
    distance = Chunk.embedding.cosine_distance(query_vec).label("distance")
    stmt = (
        select(
            Chunk.document_id,
            Chunk.section,
            Chunk.page,
            Chunk.content,
            Document.filename,
            distance,
        )
        .join(Document, Document.id == Chunk.document_id)
        .order_by(distance)
        .limit(top_k)
    )
    rows = db.execute(stmt).all()

    results = []
    for r in rows:
        score = round(1.0 - float(r.distance), 4)
        results.append(
            {
                "document_id": r.document_id,
                "document": r.filename,
                "section": r.section,
                "page": r.page,
                "excerpt": r.content,
                "score": score,
            }
        )
    return results


def search(db: Session, query: str, top_k: int | None = None) -> list[dict]:
    """Pure retrieval -- no LLM. Powers /api/search and the RAG Explorer."""
    top_k = top_k or settings.retrieval_top_k
    request_id = new_request_id()
    with timed() as elapsed:
        results = _retrieve(db, query, top_k)
        retrieval_ms = elapsed()

    log_event(
        request_id=request_id,
        endpoint="search",
        retrieval_ms=retrieval_ms,
        chunks=len(results),
        top_score=results[0]["score"] if results else None,
    )
    return results


def _build_context(chunks: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        loc = c["document"]
        if c.get("section"):
            loc += f" · {c['section']}"
        if c.get("page") is not None:
            loc += f" · p.{c['page']}"
        blocks.append(f"[{i}] Source: {loc}\n{c['excerpt']}")
    return "\n\n".join(blocks)


def chat(db: Session, question: str, top_k: int | None = None) -> dict:
    """Grounded RAG chat.

    Retrieves context, applies the confidence threshold, and only then asks the
    LLM. Returns {answer, sources, status}.
    """
    top_k = top_k or settings.retrieval_top_k
    request_id = new_request_id()

    with timed() as elapsed:
        retrieved = _retrieve(db, question, top_k)
        retrieval_ms = elapsed()

    # Keep only chunks that clear the similarity threshold.
    trusted = [c for c in retrieved if c["score"] >= settings.similarity_threshold]

    if not trusted:
        log_event(
            request_id=request_id,
            endpoint="chat",
            retrieval_ms=retrieval_ms,
            llm_ms=0,
            chunks=0,
            model=settings.ollama_model,
            status=INSUFFICIENT_CONTEXT,
        )
        return {
            "answer": "Não encontrei informação suficiente nos documentos indexados.",
            "sources": [],
            "status": "insufficient_context",
        }

    context = _build_context(trusted)
    prompt = f"Retrieved context:\n\n{context}\n\nQuestion: {question}\n\nAnswer:"

    llm = get_llm_provider()
    with timed() as elapsed:
        raw = llm.generate(system=SYSTEM_PROMPT, prompt=prompt)
        llm_ms = elapsed()

    # Respect the model's own insufficiency signal.
    if INSUFFICIENT_CONTEXT in raw.upper():
        status = "insufficient_context"
        answer = "Não encontrei informação suficiente nos documentos indexados."
        sources: list[dict] = []
    else:
        status = "answered"
        answer = raw
        sources = trusted

    log_event(
        request_id=request_id,
        endpoint="chat",
        retrieval_ms=retrieval_ms,
        llm_ms=llm_ms,
        chunks=len(trusted),
        model=settings.ollama_model,
        status=status,
    )
    return {"answer": answer, "sources": sources, "status": status}
