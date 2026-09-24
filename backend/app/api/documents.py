"""Document ingestion, management and insights endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.embeddings.ollama_embeddings import EmbeddingError
from app.ingestion import ExtractionError
from app.models.schemas import DocumentOut, InsightsOut, UploadResult
from app.services import document_service as svc
from app.services import insights_service as insights_svc

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _to_out(doc, insights=None) -> DocumentOut:
    out = DocumentOut.model_validate(doc)
    if insights is not None:
        out.category = insights.category or None
        out.tags = insights.tags or []
        out.has_insights = insights.status == "SUCCESS"
    return out


@router.post("/upload", response_model=UploadResult)
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    data = file.file.read()
    try:
        document, duplicate = svc.ingest_document(db, file.filename or "upload", data)
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except EmbeddingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return UploadResult(
        document_id=document.id,
        filename=document.filename,
        chunks=document.chunk_count,
        status="duplicate" if duplicate else document.status,
        duplicate=duplicate,
    )


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    docs = svc.list_documents(db)
    out = []
    for d in docs:
        ins = insights_svc.get_insights(db, d.id)
        out.append(_to_out(d, ins))
    return out


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: Session = Depends(get_db)):
    doc = svc.get_document(db, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return _to_out(doc, insights_svc.get_insights(db, document_id))


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    if not svc.delete_document(db, document_id):
        raise HTTPException(status_code=404, detail="Document not found")


@router.post("/{document_id}/insights", response_model=InsightsOut)
def create_insights(document_id: int, db: Session = Depends(get_db)):
    try:
        return insights_svc.generate_insights(db, document_id)
    except insights_svc.InsightsError as exc:
        # Document not found -> 404; LLM/JSON issues -> 503.
        code = 404 if "not found" in str(exc).lower() else 503
        raise HTTPException(status_code=code, detail=str(exc)) from exc


@router.get("/{document_id}/insights", response_model=InsightsOut)
def read_insights(document_id: int, db: Session = Depends(get_db)):
    row = insights_svc.get_insights(db, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="No insights for this document")
    return row
