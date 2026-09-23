"""Load the evaluation dataset shared with the CLI harness (evaluation/dataset.json)."""
from __future__ import annotations

import json
from pathlib import Path

# backend/app/evaluation/dataset.py -> repo root is three parents up from app/.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DATASETS = {"default": _REPO_ROOT / "evaluation" / "dataset.json"}


def load_dataset(name: str = "default") -> list[dict]:
    path = _DATASETS.get(name)
    if path is None or not path.exists():
        raise FileNotFoundError(f"Unknown dataset: {name}")
    return json.loads(path.read_text(encoding="utf-8"))
