"""Lexical (BM25) reranker — a dependency-free local reranker.

A cross-encoder (e.g. bge-reranker) would need a heavy PyTorch/transformers stack;
to keep V2 lean and reproducible on modest hardware, the default reranker scores
each candidate with BM25 computed over the candidate set itself. This provides a
lexical relevance signal that is independent of the embedding cosine similarity and
genuinely reorders results. Swapping in a cross-encoder is a V3 upgrade behind the
same RerankerProvider interface.
"""
from __future__ import annotations

import math
import re

from app.rag.reranker.base import RerankerProvider

_TOKEN = re.compile(r"[a-zA-Z0-9À-ſ]+")
_K1 = 1.5
_B = 0.75


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if len(t) > 1]


class LexicalReranker(RerankerProvider):
    name = "lexical"

    def rerank(self, query: str, chunks: list[dict]) -> list[dict]:
        if not chunks:
            return []

        docs = [_tokenize(c["excerpt"]) for c in chunks]
        lengths = [len(d) for d in docs]
        avg_len = sum(lengths) / len(lengths) if lengths else 0.0

        # Document frequency across the candidate set (used as the corpus for IDF).
        n = len(docs)
        df: dict[str, int] = {}
        for d in docs:
            for term in set(d):
                df[term] = df.get(term, 0) + 1

        q_terms = set(_tokenize(query))

        raw_scores: list[float] = []
        for tokens, length in zip(docs, lengths, strict=True):
            tf: dict[str, int] = {}
            for term in tokens:
                tf[term] = tf.get(term, 0) + 1
            score = 0.0
            for term in q_terms:
                if term not in tf:
                    continue
                idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
                denom = tf[term] + _K1 * (1 - _B + _B * (length / avg_len if avg_len else 1))
                score += idf * (tf[term] * (_K1 + 1)) / denom
            raw_scores.append(score)

        # Normalize to 0..1 for display; ranking order is unaffected.
        hi = max(raw_scores) if raw_scores else 0.0
        out = []
        for c, raw in zip(chunks, raw_scores, strict=True):
            item = dict(c)
            item["rerank_score"] = round(raw / hi, 4) if hi > 0 else 0.0
            out.append(item)

        # Stable sort keeps the original (vector) order among ties, so a zero-signal
        # rerank preserves the retrieval ranking.
        out.sort(key=lambda x: x["rerank_score"], reverse=True)
        return out
