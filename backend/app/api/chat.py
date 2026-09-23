"""Grounded RAG chat endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.embeddings.ollama_embeddings import EmbeddingError
from app.llm import LLMError
from app.models.schemas import ChatRequest, ChatResponse
from app.rag import chat as rag_chat

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    try:
        result = rag_chat(db, req.question, req.top_k)
    except EmbeddingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ChatResponse(**result)
