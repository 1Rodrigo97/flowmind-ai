"""Pure unit tests for the lexical reranker (T5: reranking changes order correctly)."""
from __future__ import annotations

from app.rag.reranker import get_reranker


def _chunk(doc: str, score: float, text: str) -> dict:
    return {
        "document_id": 1,
        "document": doc,
        "section": None,
        "page": None,
        "excerpt": text,
        "score": score,
    }


def test_reranker_reorders_by_lexical_relevance():
    reranker = get_reranker("lexical")
    # Vector order puts the weakly-matching chunk first; lexical match should promote
    # the chunk that actually contains the query terms.
    candidates = [
        _chunk("a.md", 0.80, "an unrelated passage about weather and gardens"),
        _chunk("b.md", 0.78, "fine-tuning updates the model weights on a dataset"),
    ]
    out = reranker.rerank("how does fine-tuning update model weights", candidates)

    assert out[0]["document"] == "b.md"  # promoted by lexical relevance
    assert out[0]["rerank_score"] >= out[1]["rerank_score"]
    assert "rerank_score" in out[0]


def test_reranker_empty():
    assert get_reranker("lexical").rerank("q", []) == []


def test_reranker_preserves_all_candidates():
    reranker = get_reranker("lexical")
    candidates = [_chunk("a.md", 0.7, "retrieval context"), _chunk("b.md", 0.6, "embeddings")]
    out = reranker.rerank("retrieval", candidates)
    assert len(out) == 2
    assert {c["document"] for c in out} == {"a.md", "b.md"}
