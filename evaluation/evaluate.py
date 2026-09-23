"""Minimal RAG evaluation harness.

Runs the questions in dataset.json against a running FlowMind AI backend and
reports:
  - Hit@K: fraction of questions whose expected document appears in the sources.
  - Term coverage: fraction of expected terms present in the answer.
  - Insufficient-context handling: correct refusals on unanswerable questions.
  - Average latency per question.

Usage:
    python evaluation/evaluate.py --api http://localhost:8000 --top-k 5

The backend must be running and the sample_documents must already be indexed
(see the README "Evaluation" section).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent


def load_dataset() -> list[dict]:
    return json.loads((HERE / "dataset.json").read_text(encoding="utf-8"))


def run(api: str, top_k: int) -> int:
    api = api.rstrip("/")
    dataset = load_dataset()

    hits = 0
    hit_total = 0
    term_hits = 0
    term_total = 0
    insufficient_correct = 0
    insufficient_total = 0
    latencies: list[float] = []

    print(f"\nFlowMind AI — RAG evaluation ({len(dataset)} questions, top_k={top_k})\n")
    print(f"{'#':>2}  {'result':<12} {'doc?':<5} {'terms':<7} {'ms':>7}  question")
    print("-" * 78)

    for i, item in enumerate(dataset, start=1):
        question = item["question"]
        # New V2 dataset schema (with backward-compatible fallbacks).
        expect_insufficient = not item.get("should_answer", not item.get("expect_insufficient", False))
        expected_documents = item.get("expected_documents")
        if expected_documents is None:
            single = item.get("expected_document")
            expected_documents = [single] if single else []

        start = time.perf_counter()
        try:
            resp = httpx.post(
                f"{api}/api/chat", json={"question": question, "top_k": top_k}, timeout=180
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            print(f"{i:>2}  ERROR: {exc}")
            continue
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)

        status = data.get("status")
        answer = (data.get("answer") or "").lower()
        sources = data.get("sources", [])
        source_docs = {s.get("document") for s in sources}

        if expect_insufficient:
            insufficient_total += 1
            ok = status == "insufficient_context"
            insufficient_correct += int(ok)
            result = "REFUSED" if ok else "HALLUCINATED"
            print(f"{i:>2}  {result:<12} {'-':<5} {'-':<7} {elapsed_ms:>7.0f}  {question[:38]}")
            continue

        # Hit@K
        hit_total += 1
        doc_hit = any(d in source_docs for d in expected_documents)
        hits += int(doc_hit)

        # Term coverage
        terms = item.get("expected_terms", [])
        present = sum(1 for t in terms if t.lower() in answer)
        term_hits += present
        term_total += len(terms)

        result = "answered" if status == "answered" else status
        term_str = f"{present}/{len(terms)}" if terms else "-"
        print(
            f"{i:>2}  {result:<12} {('YES' if doc_hit else 'no'):<5} "
            f"{term_str:<7} {elapsed_ms:>7.0f}  {question[:38]}"
        )

    print("-" * 78)
    hit_at_k = hits / hit_total if hit_total else 0.0
    term_cov = term_hits / term_total if term_total else 0.0
    refusal = insufficient_correct / insufficient_total if insufficient_total else 0.0
    avg_ms = sum(latencies) / len(latencies) if latencies else 0.0

    print(f"\nHit@{top_k} (expected source):     {hit_at_k:.0%}  ({hits}/{hit_total})")
    print(f"Expected-term coverage:       {term_cov:.0%}  ({term_hits}/{term_total})")
    print(
        f"Insufficient-context correct: {refusal:.0%}  "
        f"({insufficient_correct}/{insufficient_total})"
    )
    print(f"Average latency:              {avg_ms:.0f} ms\n")

    # Non-zero exit if retrieval is clearly broken, so CI can catch regressions.
    return 0 if hit_at_k >= 0.5 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="FlowMind AI RAG evaluation")
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    raise SystemExit(run(args.api, args.top_k))


if __name__ == "__main__":
    main()
