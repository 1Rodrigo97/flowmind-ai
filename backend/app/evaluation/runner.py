"""Experiment runner: evaluate a RAG configuration over a dataset and persist it.

Retrieval metrics (Hit@K, MRR, Precision@K, Recall@K) and the refusal decision are
deterministic and computed without the LLM. Answer generation (and LLM latency) is
optional via ``include_answer`` and kept separate from the deterministic metrics.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.evaluation import metrics as M
from app.evaluation.dataset import load_dataset
from app.evaluation.profiles import ensure_profile
from app.models import RagExperiment, RagExperimentResult
from app.models.schemas import ExperimentConfig
from app.rag import chat as rag_chat
from app.rag import retrieve

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _commit_sha() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def run_experiment(
    db: Session,
    config: ExperimentConfig,
    dataset: str = "default",
    include_answer: bool = False,
) -> RagExperiment:
    cases = load_dataset(dataset)
    profile = settings.index_profile(
        embedding_model=config.embedding_model,
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )
    ensure_profile(db, profile, config.chunk_size, config.chunk_overlap)

    started = time.perf_counter()
    rows: list[RagExperimentResult] = []

    hits = mrr = prec = rec = terms = 0.0
    pos_total = neg_total = 0
    answered_count = correct_refusals = 0
    retr_latencies: list[float] = []
    llm_latencies: list[float] = []

    for i, case in enumerate(cases, start=1):
        question = case["question"]
        qid = case.get("id", f"case-{i}")
        expected_docs = case.get("expected_documents", [])
        expected_terms = case.get("expected_terms", [])
        should_answer = case.get("should_answer", True)

        t0 = time.perf_counter()
        result = retrieve(
            db,
            question,
            top_k=config.top_k,
            profile=profile,
            rerank=config.reranker_enabled,
            reranker_model=config.reranker_model,
            candidates=config.reranker_candidates,
        )
        retr_ms = (time.perf_counter() - t0) * 1000
        retr_latencies.append(retr_ms)

        final = result["final"]
        retrieved_docs = [c["document"] for c in final]
        evidence = " ".join(c["excerpt"] for c in final)

        # Deterministic refusal decision (pre-LLM gate).
        answered = any(c["score"] >= config.similarity_threshold for c in final)

        row = RagExperimentResult(
            question_id=qid,
            question=question,
            retrieved_documents=retrieved_docs,
            answered=answered,
        )

        if should_answer:
            pos_total += 1
            row.hit = M.hit_at_k(retrieved_docs, expected_docs)
            row.reciprocal_rank = M.reciprocal_rank(retrieved_docs, expected_docs)
            row.precision_at_k = M.precision_at_k(retrieved_docs, expected_docs)
            row.recall_at_k = M.recall_at_k(retrieved_docs, expected_docs)
            row.terms_matched = M.terms_match(evidence, expected_terms)
            hits += int(row.hit)
            mrr += row.reciprocal_rank
            prec += row.precision_at_k
            rec += row.recall_at_k
            terms += row.terms_matched
            answered_count += int(answered)
        else:
            neg_total += 1
            row.correct_refusal = not answered
            correct_refusals += int(row.correct_refusal)

        if include_answer and should_answer:
            t1 = time.perf_counter()
            ans = rag_chat(db, question, top_k=config.top_k)
            llm_latencies.append((time.perf_counter() - t1) * 1000)
            row.answered = ans["status"] == "answered"

        rows.append(row)

    duration_ms = round((time.perf_counter() - started) * 1000, 2)

    def avg(total: float, n: int) -> float:
        return round(total / n, 4) if n else 0.0

    metrics = {
        "hit_at_k": avg(hits, pos_total),
        "mrr": avg(mrr, pos_total),
        "precision_at_k": avg(prec, pos_total),
        "recall_at_k": avg(rec, pos_total),
        "expected_terms_match": avg(terms, pos_total),
        "answer_rate": avg(answered_count, pos_total),
        "correct_refusal_rate": avg(correct_refusals, neg_total),
        "latency_retrieval_ms": avg(sum(retr_latencies), len(retr_latencies)),
        "latency_llm_ms": avg(sum(llm_latencies), len(llm_latencies)),
        "positives": pos_total,
        "negatives": neg_total,
        "top_k": config.top_k,
    }

    experiment = RagExperiment(
        name=config.name,
        config=config.model_dump(),
        index_profile=profile,
        dataset_name=dataset,
        dataset_size=len(cases),
        metrics=metrics,
        commit_sha=_commit_sha(),
        duration_ms=duration_ms,
    )
    experiment.results = rows
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return experiment
