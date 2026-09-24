"""Automation endpoints (n8n pillar). Protected by the automation service token."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_automation_token
from app.core.database import get_db
from app.models import AutomationRun
from app.models.schemas import (
    AutomationRunOut,
    AutomationStats,
    ScanResponse,
)
from app.services import automation_service as auto

router = APIRouter(prefix="/api/automation", tags=["automation"])


@router.post("/scan", response_model=ScanResponse, dependencies=[Depends(require_automation_token)])
def scan_inbox(workflow: str = "inbox", db: Session = Depends(get_db)):
    """Scan the inbox and process each supported file. Called by the n8n schedule."""
    runs = auto.process_inbox(db, workflow=workflow)
    return ScanResponse(processed=len(runs), runs=runs)


@router.get("/runs", response_model=list[AutomationRunOut])
def list_runs(db: Session = Depends(get_db)):
    return list(db.scalars(select(AutomationRun).order_by(AutomationRun.started_at.desc())))


@router.get("/stats", response_model=AutomationStats)
def automation_stats(db: Session = Depends(get_db)):
    return auto.stats(db)


@router.get("/runs/{run_id}", response_model=AutomationRunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(AutomationRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post(
    "/runs/{run_id}/retry",
    response_model=AutomationRunOut,
    dependencies=[Depends(require_automation_token)],
)
def retry_run(run_id: int, db: Session = Depends(get_db)):
    try:
        return auto.retry_run(db, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
