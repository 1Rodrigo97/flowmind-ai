"""Pure unit tests for retrieval metrics (T1 Hit@K, T2 MRR, T3 Precision@K, T4 negatives)."""
from __future__ import annotations

from app.evaluation import metrics as M


def test_hit_at_k():
    assert M.hit_at_k(["a.md", "b.md"], ["b.md"]) is True
    assert M.hit_at_k(["a.md", "b.md"], ["z.md"]) is False
    assert M.hit_at_k([], ["b.md"]) is False


def test_reciprocal_rank():
    # first relevant at rank 1
    assert M.reciprocal_rank(["b.md", "a.md"], ["b.md"]) == 1.0
    # first relevant at rank 3
    assert M.reciprocal_rank(["a.md", "c.md", "b.md"], ["b.md"]) == round(1 / 3, 4)
    # none relevant
    assert M.reciprocal_rank(["a.md"], ["b.md"]) == 0.0


def test_precision_at_k():
    # 2 of 4 retrieved chunks belong to expected docs
    assert M.precision_at_k(["a.md", "a.md", "x.md", "y.md"], ["a.md"]) == 0.5
    assert M.precision_at_k([], ["a.md"]) == 0.0


def test_recall_at_k():
    # 1 of 2 expected docs retrieved
    assert M.recall_at_k(["a.md", "a.md", "x.md"], ["a.md", "b.md"]) == 0.5
    # both expected retrieved
    assert M.recall_at_k(["a.md", "b.md"], ["a.md", "b.md"]) == 1.0
    assert M.recall_at_k(["a.md"], []) == 0.0


def test_terms_match():
    assert M.terms_match("uses retrieval and context here", ["retrieval", "context"]) == 1.0
    assert M.terms_match("only retrieval", ["retrieval", "context"]) == 0.5
    assert M.terms_match("text", []) == 0.0


def test_negative_case_metrics():
    # A negative case has no expected documents: nothing is relevant.
    assert M.hit_at_k(["a.md", "b.md"], []) is False
    assert M.reciprocal_rank(["a.md"], []) == 0.0
