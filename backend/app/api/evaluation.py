"""RAG evaluation lab endpoints (V2)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.embeddings.ollama_embeddings import EmbeddingError
from app.evaluation.runner import run_experiment
from app.models import RagExperiment
from app.models.schemas import (
    CompareRequest,
    CompareResponse,
    ExperimentDetail,
    ExperimentSummary,
    RunRequest,
)

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])

_DELTA_METRICS = [
    "hit_at_k",
    "mrr",
    "precision_at_k",
    "recall_at_k",
    "correct_refusal_rate",
    "latency_retrieval_ms",
]


def _detail(exp: RagExperiment) -> ExperimentDetail:
    return ExperimentDetail(
        id=exp.id,
        name=exp.name,
        index_profile=exp.index_profile,
        dataset_name=exp.dataset_name,
        dataset_size=exp.dataset_size,
        metrics=exp.metrics,
        commit_sha=exp.commit_sha,
        duration_ms=exp.duration_ms,
        created_at=exp.created_at,
        config=exp.config,
        results=[
            {
                "question_id": r.question_id,
                "question": r.question,
                "retrieved_documents": r.retrieved_documents,
                "hit": r.hit,
                "reciprocal_rank": r.reciprocal_rank,
                "precision_at_k": r.precision_at_k,
                "recall_at_k": r.recall_at_k,
                "answered": r.answered,
                "correct_refusal": r.correct_refusal,
                "terms_matched": r.terms_matched,
            }
            for r in exp.results
        ],
    )


@router.get("/experiments", response_model=list[ExperimentSummary])
def list_experiments(db: Session = Depends(get_db)):
    return list(db.scalars(select(RagExperiment).order_by(RagExperiment.created_at.desc())))


@router.post("/run", response_model=ExperimentDetail)
def run(req: RunRequest, db: Session = Depends(get_db)):
    try:
        exp = run_experiment(db, req.config, req.dataset, req.include_answer)
    except EmbeddingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _detail(exp)


@router.get("/experiments/{experiment_id}", response_model=ExperimentDetail)
def get_experiment(experiment_id: int, db: Session = Depends(get_db)):
    exp = db.get(RagExperiment, experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return _detail(exp)


@router.post("/compare", response_model=CompareResponse)
def compare(req: CompareRequest, db: Session = Depends(get_db)):
    exps = [db.get(RagExperiment, i) for i in req.experiment_ids]
    if any(e is None for e in exps):
        raise HTTPException(status_code=404, detail="One or more experiments not found")

    rows = [{"id": e.id, "name": e.name, "metrics": e.metrics} for e in exps]
    base = exps[0].metrics
    deltas: dict[str, dict[int, float]] = {}
    for metric in _DELTA_METRICS:
        b = base.get(metric)
        if b is None:
            continue
        deltas[metric] = {
            e.id: round((e.metrics.get(metric, 0.0) or 0.0) - b, 4) for e in exps[1:]
        }
    return CompareResponse(experiments=rows, deltas=deltas)
