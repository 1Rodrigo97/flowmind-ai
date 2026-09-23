"""Lightweight structured logging helpers for observability.

Logs one JSON line per request with timing and RAG metrics. Document content is
never logged in full -- only counts and identifiers.
"""
from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager

logger = logging.getLogger("flowmind")

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def log_event(**fields) -> None:
    """Emit a single structured JSON log line."""
    logger.info(json.dumps(fields, ensure_ascii=False, default=str))


@contextmanager
def timed():
    """Context manager yielding a callable that returns elapsed ms."""
    start = time.perf_counter()
    yield lambda: round((time.perf_counter() - start) * 1000, 2)
