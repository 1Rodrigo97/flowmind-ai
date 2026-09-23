"""Deterministic retrieval and answer metrics computed from an expected dataset.

Definitions (chunk-level, relevance judged by document name):
  Hit@K       -- 1 if any of the K retrieved chunks belongs to an expected
                 document, else 0. Averaged over the dataset it is the hit rate.
  MRR         -- reciprocal of the rank of the first retrieved chunk that belongs
                 to an expected document (0 if none). Averaged = Mean Reciprocal Rank.
  Precision@K -- fraction of the K retrieved chunks that belong to expected documents.
  Recall@K    -- fraction of the distinct expected documents that were retrieved.

No score is invented: everything is derived from the retrieved documents versus the
dataset's expected_documents / expected_terms.
"""
from __future__ import annotations


def _relevant_flags(retrieved_docs: list[str], expected_docs: list[str]) -> list[bool]:
    expected = set(expected_docs)
    return [doc in expected for doc in retrieved_docs]


def hit_at_k(retrieved_docs: list[str], expected_docs: list[str]) -> bool:
    return any(_relevant_flags(retrieved_docs, expected_docs))


def reciprocal_rank(retrieved_docs: list[str], expected_docs: list[str]) -> float:
    for i, is_rel in enumerate(_relevant_flags(retrieved_docs, expected_docs), start=1):
        if is_rel:
            return round(1.0 / i, 4)
    return 0.0


def precision_at_k(retrieved_docs: list[str], expected_docs: list[str]) -> float:
    if not retrieved_docs:
        return 0.0
    flags = _relevant_flags(retrieved_docs, expected_docs)
    return round(sum(flags) / len(flags), 4)


def recall_at_k(retrieved_docs: list[str], expected_docs: list[str]) -> float:
    if not expected_docs:
        return 0.0
    retrieved = set(retrieved_docs)
    found = sum(1 for d in set(expected_docs) if d in retrieved)
    return round(found / len(set(expected_docs)), 4)


def terms_match(text: str, expected_terms: list[str]) -> float:
    """Fraction of expected terms present in the given text (case-insensitive).

    Used as a deterministic groundedness proxy over the retrieved evidence.
    """
    if not expected_terms:
        return 0.0
    low = text.lower()
    present = sum(1 for t in expected_terms if t.lower() in low)
    return round(present / len(expected_terms), 4)
