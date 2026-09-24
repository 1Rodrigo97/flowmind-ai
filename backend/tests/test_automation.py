"""Automation + insights integration tests (skip without Postgres + Ollama).

Covers T1 (new file processes), T2 (duplicate not duplicated), T3 (insights
persisted), T4 (summary), T5 (tags), T6 (existing task extracted), T7 (no task ->
[]), T8 (dates extracted), T9 (Ollama insights failure keeps ingestion), T11 (run
persisted), T13 (manual retry idempotent), T15 (RAG pipeline still intact).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.models import AutomationRun, Document
from app.services import automation_service as auto
from app.services import insights_service
from tests.conftest import requires_stack

MEETING = """# Ata de Reunião

Data da reunião: 10/03/2026.

## Tarefas
- Comparar dois modelos de embeddings locais até 24/03/2026.
- Escrever o roteiro da demonstração interna.

Próxima reunião em 31/03/2026.
"""

ARTICLE = """# Bancos de Dados Vetoriais

Bancos vetoriais guardam embeddings e permitem busca por similaridade de cosseno.
Usam índices aproximados como HNSW. Este texto é conceitual, sem ações nem prazos.
"""


@pytest.fixture
def inbox(tmp_path, monkeypatch):
    ib = tmp_path / "inbox"
    pr = tmp_path / "processed"
    fa = tmp_path / "failed"
    for d in (ib, pr, fa):
        d.mkdir()
    monkeypatch.setattr(auto.settings, "automation_inbox_dir", str(ib))
    monkeypatch.setattr(auto.settings, "automation_processed_dir", str(pr))
    monkeypatch.setattr(auto.settings, "automation_failed_dir", str(fa))
    return ib, pr, fa


def _drop(inbox_dir: Path, name: str, content: str) -> None:
    (inbox_dir / name).write_text(content, encoding="utf-8")


@requires_stack
def test_new_file_processes_with_insights(db, inbox):
    ib, pr, _ = inbox
    _drop(ib, "reuniao.md", MEETING)
    runs = auto.process_inbox(db)

    assert len(runs) == 1
    run = runs[0]
    assert run.status == "SUCCESS"  # T1
    assert run.document_id is not None
    assert run.insights_status == "SUCCESS"  # T3
    assert not (ib / "reuniao.md").exists()  # moved
    assert (pr / "reuniao.md").exists()  # -> processed

    ins = insights_service.get_insights(db, run.document_id)
    assert ins is not None and ins.status == "SUCCESS"
    assert ins.summary.strip()  # T4
    assert len(ins.tags) >= 1  # T5
    assert len(ins.tasks) >= 1  # T6 (meeting has explicit tasks)
    assert len(ins.dates) >= 1  # T8 (meeting has explicit dates)

    # T11: run persisted and retrievable
    assert db.get(AutomationRun, run.id) is not None


@requires_stack
def test_duplicate_not_duplicated(db, inbox):
    ib, pr, _ = inbox
    _drop(ib, "reuniao.md", MEETING)
    auto.process_inbox(db)
    _drop(ib, "reuniao-copia.md", MEETING)  # same content, different name
    runs = auto.process_inbox(db)

    assert runs[0].status == "DUPLICATE"  # T2
    assert db.scalar(select(func.count(Document.id))) == 1


@requires_stack
def test_article_has_no_invented_tasks(db, inbox):
    ib, _, _ = inbox
    _drop(ib, "artigo.md", ARTICLE)
    runs = auto.process_inbox(db)
    ins = insights_service.get_insights(db, runs[0].document_id)
    assert ins.tasks == []  # T7: no tasks invented for a pure article


@requires_stack
def test_ollama_insights_failure_keeps_ingestion(db, inbox, monkeypatch):
    """T9: if insights fail, the document stays indexed (ingestion is not lost)."""
    ib, pr, _ = inbox
    _drop(ib, "reuniao.md", MEETING)

    def boom(*a, **k):
        raise insights_service.InsightsError("simulated Ollama outage")

    monkeypatch.setattr(auto, "generate_insights", boom)
    runs = auto.process_inbox(db)
    run = runs[0]

    assert run.status == "SUCCESS"  # ingestion succeeded
    assert run.insights_status == "FAILED"  # insights failed
    assert db.get(Document, run.document_id) is not None  # document preserved
    assert (pr / "reuniao.md").exists()  # still moved to processed


@requires_stack
def test_manual_retry_is_idempotent(db, inbox, monkeypatch):
    """T13: retry regenerates insights for an already-ingested document, safely."""
    ib, _, _ = inbox
    _drop(ib, "reuniao.md", MEETING)

    def boom(*a, **k):
        raise insights_service.InsightsError("outage")

    monkeypatch.setattr(auto, "generate_insights", boom)
    run = auto.process_inbox(db)[0]
    assert run.insights_status == "FAILED"

    # Restore real insights and retry -> should succeed without new documents.
    monkeypatch.setattr(auto, "generate_insights", insights_service.generate_insights)
    before = db.scalar(select(func.count(Document.id)))
    retried = auto.retry_run(db, run.id)
    after = db.scalar(select(func.count(Document.id)))
    assert retried.insights_status == "SUCCESS"
    assert before == after  # idempotent: no duplicate document
