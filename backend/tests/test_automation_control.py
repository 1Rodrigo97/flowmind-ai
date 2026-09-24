"""Automation control tests: retry limit (T10) and token validation (T12)."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api.deps import require_automation_token
from app.services import automation_service as auto
from tests.conftest import requires_db


# ---- T12: token validation (pure, no DB / no Ollama) ----


def test_token_disabled_when_empty(monkeypatch):
    monkeypatch.setattr(auto.settings, "automation_token", "")
    # No exception when auth is disabled.
    assert require_automation_token(authorization=None) is None


def test_token_missing_rejected(monkeypatch):
    from app.api import deps

    monkeypatch.setattr(deps.settings, "automation_token", "secret")
    with pytest.raises(HTTPException) as exc:
        require_automation_token(authorization=None)
    assert exc.value.status_code == 401


def test_token_invalid_rejected(monkeypatch):
    from app.api import deps

    monkeypatch.setattr(deps.settings, "automation_token", "secret")
    with pytest.raises(HTTPException) as exc:
        require_automation_token(authorization="Bearer wrong")
    assert exc.value.status_code == 403


def test_token_valid_accepted(monkeypatch):
    from app.api import deps

    monkeypatch.setattr(deps.settings, "automation_token", "secret")
    assert require_automation_token(authorization="Bearer secret") is None


# ---- T10: retry respects the attempt limit (needs Postgres, no Ollama) ----


@requires_db
def test_retry_limit_then_failed(db, tmp_path, monkeypatch):
    ib, pr, fa = tmp_path / "inbox", tmp_path / "processed", tmp_path / "failed"
    for d in (ib, pr, fa):
        d.mkdir()
    monkeypatch.setattr(auto.settings, "automation_inbox_dir", str(ib))
    monkeypatch.setattr(auto.settings, "automation_processed_dir", str(pr))
    monkeypatch.setattr(auto.settings, "automation_failed_dir", str(fa))
    monkeypatch.setattr(auto.settings, "automation_max_attempts", 3)

    # An empty file fails ingestion (extraction) without needing Ollama.
    (ib / "bad.md").write_bytes(b"")

    r1 = auto.process_inbox(db)[0]
    assert r1.status == "PENDING" and r1.attempts == 1
    assert (ib / "bad.md").exists()  # kept for retry

    r2 = auto.process_inbox(db)[0]
    assert r2.status == "PENDING" and r2.attempts == 2

    r3 = auto.process_inbox(db)[0]
    assert r3.status == "FAILED" and r3.attempts == 3  # T10: give up at the limit
    assert (fa / "bad.md").exists()  # moved to failed only after terminal result
    assert not (ib / "bad.md").exists()
