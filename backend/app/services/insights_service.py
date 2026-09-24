"""Document Insights: grounded, structured analysis of an indexed document.

The LLM produces a JSON object (summary, category, tags, tasks, dates) using ONLY
the document text. Tasks and dates are never invented: if the document has none,
the lists come back empty. Results are persisted so they are not recomputed.
"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import log_event, timed
from app.llm import LLMError, get_llm_provider
from app.models import Document, DocumentInsights

INSIGHTS_SYSTEM = (
    "You are FlowMind AI's document analyst. Analyze ONLY the document text provided "
    "and return a single JSON object with keys: summary (2-4 sentences), category (a "
    "short topic label), tags (array of 3-6 short strings), tasks (array of objects "
    '{"text": string, "due_date": string-or-null}), and dates (array of date strings '
    "mentioned in the document). Extract tasks and dates ONLY if they appear in the "
    "document. If there are no tasks, return an empty array. If there are no dates, "
    "return an empty array. Do not invent tasks, dates, names or facts. Respond in the "
    "language of the document. Return JSON only."
)

_MAX_CHARS = 6000


class InsightsError(RuntimeError):
    """Raised when insights cannot be generated (e.g. LLM unavailable, bad JSON)."""


def _coerce(data: dict) -> dict:
    tasks = []
    for t in data.get("tasks") or []:
        if isinstance(t, dict) and t.get("text"):
            tasks.append({"text": str(t["text"]), "due_date": t.get("due_date")})
        elif isinstance(t, str) and t.strip():
            tasks.append({"text": t.strip(), "due_date": None})
    tags = [str(x) for x in (data.get("tags") or []) if str(x).strip()]
    dates = [str(x) for x in (data.get("dates") or []) if str(x).strip()]
    return {
        "summary": str(data.get("summary") or "").strip(),
        "category": str(data.get("category") or "").strip(),
        "tags": tags,
        "tasks": tasks,
        "dates": dates,
    }


def _parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            return json.loads(raw[start : end + 1])
        raise


def _analyze(document: Document) -> dict:
    text = (document.raw_text or "")[:_MAX_CHARS]
    if not text.strip():
        raise InsightsError("Document has no text to analyze.")
    prompt = f"Document '{document.filename}':\n\n{text}\n\nReturn the JSON object."
    llm = get_llm_provider()
    try:
        raw = llm.generate(system=INSIGHTS_SYSTEM, prompt=prompt, json_mode=True)
    except LLMError as exc:
        raise InsightsError(str(exc)) from exc
    try:
        return _coerce(_parse_json(raw))
    except (json.JSONDecodeError, TypeError) as exc:
        raise InsightsError(f"Model returned invalid JSON: {exc}") from exc


def get_insights(db: Session, document_id: int) -> DocumentInsights | None:
    return db.scalar(
        select(DocumentInsights).where(DocumentInsights.document_id == document_id)
    )


def generate_insights(
    db: Session, document_id: int, force: bool = False
) -> DocumentInsights:
    """Generate (or return cached) insights for a document and persist them."""
    document = db.get(Document, document_id)
    if document is None:
        raise InsightsError(f"Document {document_id} not found.")

    existing = get_insights(db, document_id)
    if existing is not None and existing.status == "SUCCESS" and not force:
        return existing

    with timed() as elapsed:
        parsed = _analyze(document)
        llm_ms = elapsed()

    row = existing or DocumentInsights(document_id=document_id)
    row.summary = parsed["summary"]
    row.category = parsed["category"]
    row.tags = parsed["tags"]
    row.tasks = parsed["tasks"]
    row.dates = parsed["dates"]
    row.model = settings.ollama_model
    row.status = "SUCCESS"
    row.error_message = None
    db.add(row)
    db.commit()
    db.refresh(row)

    log_event(
        endpoint="insights",
        document_id=document_id,
        llm_ms=llm_ms,
        model=settings.ollama_model,
        tags=len(row.tags),
        tasks=len(row.tasks),
        dates=len(row.dates),
    )
    return row
