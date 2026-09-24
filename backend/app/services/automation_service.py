"""Automation service: process files dropped in the inbox.

The API is the boundary (n8n calls FastAPI, which owns file movement and the DB).
Flow per file: ingest (dedupe by SHA-256) -> generate insights -> move to
processed/, recording an AutomationRun. Ingestion success and insights success are
tracked separately: if the LLM is down, the document stays indexed and available in
the Assistant while insights are marked FAILED for later retry -- nothing is lost.
"""
from __future__ import annotations

import shutil
import time
import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import log_event
from app.models import AutomationRun, Document
from app.services import document_service as docs
from app.services.insights_service import InsightsError, generate_insights

SUPPORTED = settings.allowed_extensions_set


def _dirs() -> tuple[Path, Path, Path]:
    inbox = Path(settings.automation_inbox_dir)
    processed = Path(settings.automation_processed_dir)
    failed = Path(settings.automation_failed_dir)
    for d in (inbox, processed, failed):
        d.mkdir(parents=True, exist_ok=True)
    return inbox, processed, failed


def _supported(path: Path) -> bool:
    return path.suffix.lower().lstrip(".") in SUPPORTED


def _move(path: Path, dest_dir: Path) -> str:
    dest = dest_dir / path.name
    if dest.exists():
        dest = dest_dir / f"{path.stem}-{uuid.uuid4().hex[:6]}{path.suffix}"
    shutil.move(str(path), str(dest))
    return str(dest)


def _prior_attempts(db: Session, filename: str) -> int:
    return (
        db.scalar(
            select(func.count(AutomationRun.id)).where(
                AutomationRun.filename == filename,
                AutomationRun.status.in_(["PENDING", "PROCESSING", "FAILED"]),
            )
        )
        or 0
    )


def process_file(db: Session, path: Path, workflow: str = "inbox") -> AutomationRun:
    """Process a single inbox file end to end, recording an AutomationRun."""
    _, processed_dir, failed_dir = _dirs()
    started = time.perf_counter()
    run = AutomationRun(
        run_uid=uuid.uuid4().hex[:12],
        workflow=workflow,
        filename=path.name,
        status="PROCESSING",
        attempts=_prior_attempts(db, path.name) + 1,
    )
    db.add(run)
    db.commit()  # persist the run first so it survives an ingestion rollback
    run_id = run.id

    try:
        data = path.read_bytes()
        run.file_hash = docs.compute_hash(data)

        document, duplicate = docs.ingest_document(db, path.name, data)
        run.document_id = document.id
        run.status = "DUPLICATE" if duplicate else "SUCCESS"

        # Insights are best-effort: a failure here must not lose the ingested document.
        try:
            generate_insights(db, document.id)
            run.insights_status = "SUCCESS"
        except InsightsError as exc:
            run.insights_status = "FAILED"
            run.error_message = f"insights: {exc}"

        run.finished_at = func.now()
        run.duration_ms = round((time.perf_counter() - started) * 1000, 2)
        db.add(run)
        db.commit()
        _move(path, processed_dir)

    except Exception as exc:  # ingestion failure
        # Roll back any partial ingestion; the run row (committed above) survives.
        db.rollback()
        run = db.get(AutomationRun, run_id)
        run.error_message = f"ingestion: {exc}"
        run.duration_ms = round((time.perf_counter() - started) * 1000, 2)
        if run.attempts >= settings.automation_max_attempts:
            run.status = "FAILED"
            run.finished_at = func.now()
            db.add(run)
            db.commit()
            _move(path, failed_dir)  # move only after a known terminal result
        else:
            run.status = "PENDING"  # leave file in inbox for the next scheduled tick
            db.add(run)
            db.commit()

    log_event(
        automation_run_id=run.run_uid,
        workflow=workflow,
        filename=run.filename,
        document_id=run.document_id,
        status=run.status,
        insights_status=run.insights_status,
        attempt=run.attempts,
        duration_ms=run.duration_ms,
    )
    return run


def process_inbox(db: Session, workflow: str = "inbox") -> list[AutomationRun]:
    """Scan the inbox and process each supported file. Idempotent across runs:
    handled files are moved out of the inbox."""
    inbox, _, _ = _dirs()
    runs: list[AutomationRun] = []
    for path in sorted(inbox.iterdir()):
        if path.is_file() and _supported(path):
            runs.append(process_file(db, path, workflow))
    return runs


def retry_run(db: Session, run_id: int) -> AutomationRun:
    """Manual, idempotent retry. If the document is already ingested, only insights
    are (re)generated; otherwise the failed file is moved back to the inbox and
    reprocessed (dedupe keeps it idempotent)."""
    run = db.get(AutomationRun, run_id)
    if run is None:
        raise ValueError("Automation run not found")

    if run.document_id and db.get(Document, run.document_id) is not None:
        try:
            generate_insights(db, run.document_id, force=True)
            run.insights_status = "SUCCESS"
            run.error_message = None
        except InsightsError as exc:
            run.insights_status = "FAILED"
            run.error_message = f"insights: {exc}"
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    # Ingestion never succeeded: try to reprocess the file if it is in failed/.
    failed_dir = Path(settings.automation_failed_dir)
    candidate = failed_dir / run.filename
    if candidate.exists():
        inbox = Path(settings.automation_inbox_dir)
        inbox.mkdir(parents=True, exist_ok=True)
        moved = shutil.move(str(candidate), str(inbox / run.filename))
        return process_file(db, Path(moved), run.workflow)

    raise ValueError("Nothing to retry: no document and no failed file found")


def stats(db: Session) -> dict:
    rows = db.execute(
        select(AutomationRun.status, func.count(AutomationRun.id)).group_by(
            AutomationRun.status
        )
    ).all()
    by_status = {s: n for s, n in rows}
    avg_ms = db.scalar(select(func.avg(AutomationRun.duration_ms))) or 0.0
    total_tasks = 0
    from app.models import DocumentInsights

    for row in db.scalars(select(DocumentInsights)):
        total_tasks += len(row.tasks or [])
    return {
        "processed": sum(by_status.values()),
        "success": by_status.get("SUCCESS", 0),
        "duplicate": by_status.get("DUPLICATE", 0),
        "failed": by_status.get("FAILED", 0),
        "pending": by_status.get("PENDING", 0),
        "avg_duration_ms": round(float(avg_ms), 2),
        "tasks_extracted": total_tasks,
    }
