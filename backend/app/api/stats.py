"""Dashboard statistics and health endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schemas import StatsResponse
from app.services import document_service as svc

router = APIRouter(tags=["stats"])


@router.get("/api/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    return svc.stats(db)


@router.get("/api/health")
def health():
    return {"status": "ok"}
