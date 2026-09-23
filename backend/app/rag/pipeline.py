"""RAG pipeline: retrieval, optional reranking and grounded chat.

Retrieval uses pgvector cosine distance, filtered by index profile so incompatible
embeddings never mix. When reranking is enabled, the top-N vector candidates are
re-scored by a RerankerProvider and the top-K kept. Grounding enforces that the LLM
answers only from retrieved context; when no chunk clears the similarity threshold,
the LLM is never asked to fabricate an answer -- INSUFFICIENT_CONTEXT is returned.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import log_event, new_request_id, timed
from app.embeddings import get_embedding_provider
from app.llm import get_llm_provider
from app.models import Chunk, Document
from app.rag.reranker import get_reranker

INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"

SYSTEM_PROMPT = (
    "You are FlowMind AI, a grounded knowledge assistant. Answer using ONLY the "
    "information present in the retrieved context below. If the context does not "
    "contain enough information to answer, reply exactly with "
    f"'{INSUFFICIENT_CONTEXT}'. Do not use prior knowledge and do not invent facts. "
    "Cite the sources you used by their document name."
)


def vector_search(
    db: Session, query: str, limit: int, profile: str | None = None
) -> list[dict]:
    """Return the top ``limit`` chunks by cosine similarity within an index profile."""
    profile = profile or settings.default_index_profile
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
        .where(Chunk.index_profile == profile)
        .order_by(distance)
        .limit(limit)
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


def retrieve(
    db: Session,
    query: str,
    *,
    top_k: int | None = None,
    profile: str | None = None,
    rerank: bool | None = None,
    reranker_model: str | None = None,
    candidates: int | None = None,
) -> dict:
    """Retrieve (and optionally rerank) chunks.

    Returns {"final": [...], "original": [...] | None, "reranker": name | None}.
    ``final`` is the top-K used for context; ``original`` is the vector-order top-K
    (only when reranking, so the UI can show the reordering).
    """
    top_k = top_k or settings.retrieval_top_k
    rerank = settings.reranker_enabled if rerank is None else rerank
    profile = profile or settings.default_index_profile

    if not rerank:
        final = vector_search(db, query, top_k, profile)
        return {"final": final, "original": None, "reranker": None}

    n = candidates or settings.reranker_candidates
    model = reranker_model or settings.reranker_model
    pool = vector_search(db, query, max(n, top_k), profile)
    original = pool[:top_k]
    reranker = get_reranker(model)
    reranked = reranker.rerank(query, pool)
    return {"final": reranked[:top_k], "original": original, "reranker": reranker.name}


def search(
    db: Session, query: str, top_k: int | None = None, rerank: bool | None = None
) -> dict:
    """Pure retrieval -- no LLM. Powers /api/search and the RAG Explorer."""
    top_k = top_k or settings.retrieval_top_k
    request_id = new_request_id()
    with timed() as elapsed:
        result = retrieve(db, query, top_k=top_k, rerank=rerank)
        retrieval_ms = elapsed()

    final = result["final"]
    log_event(
        request_id=request_id,
        endpoint="search",
        retrieval_ms=retrieval_ms,
        chunks=len(final),
        reranker=result["reranker"],
        top_score=final[0]["score"] if final else None,
    )
    return {
        "query": query,
        "results": final,
        "reranker": result["reranker"],
        "original": result["original"],
    }


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

    Retrieves context (with reranking when enabled), applies the confidence
    threshold on the semantic similarity, and only then asks the LLM.
    Returns {answer, sources, status}.
    """
    top_k = top_k or settings.retrieval_top_k
    request_id = new_request_id()

    with timed() as elapsed:
        retrieved = retrieve(db, question, top_k=top_k)["final"]
        retrieval_ms = elapsed()

    # Grounding gate is on the semantic similarity score, not the rerank score.
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
