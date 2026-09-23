"""Document ingestion and management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.embeddings.ollama_embeddings import EmbeddingError
from app.ingestion import ExtractionError
from app.models.schemas import DocumentOut, UploadResult
from app.services import document_service as svc

router = APIRouter(prefix="/api/documents", tags=["documents"])


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
    return svc.list_documents(db)


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: Session = Depends(get_db)):
    doc = svc.get_document(db, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    if not svc.delete_document(db, document_id):
        raise HTTPException(status_code=404, detail="Document not found")
