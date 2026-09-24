"""Pure unit tests for insights JSON parsing/coercion (no LLM, no DB)."""
from __future__ import annotations

from app.services.insights_service import _coerce, _parse_json


def test_parse_plain_json():
    assert _parse_json('{"a": 1}') == {"a": 1}


def test_parse_json_embedded_in_text():
    raw = 'Here is the result: {"summary": "x", "tags": []} thanks'
    assert _parse_json(raw)["summary"] == "x"


def test_coerce_defaults_empty_lists():
    out = _coerce({"summary": "s", "category": "c"})
    assert out["tags"] == []
    assert out["tasks"] == []
    assert out["dates"] == []


def test_coerce_tasks_shapes():
    out = _coerce(
        {
            "tasks": [
                {"text": "do X", "due_date": "2026-03-24"},
                "do Y",
                {"nope": 1},
            ]
        }
    )
    assert out["tasks"] == [
        {"text": "do X", "due_date": "2026-03-24"},
        {"text": "do Y", "due_date": None},
    ]


def test_coerce_filters_blank_tags_and_dates():
    out = _coerce({"tags": ["RAG", "", "LLM"], "dates": ["2026-05-15", " "]})
    assert out["tags"] == ["RAG", "LLM"]
    assert out["dates"] == ["2026-05-15"]
