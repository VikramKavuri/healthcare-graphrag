"""Convert the synthetic Excel tables into a single runtime JSON dataset.

This is a build-time / developer-only utility. It depends on pandas and
openpyxl, which are intentionally *not* part of the serverless runtime
dependencies. Run it whenever the source spreadsheets in ``data/`` change:

    python scripts/prepare_data.py

The output (``graphrag/dataset.json``) is committed and loaded by the
serverless API at runtime using only the Python standard library, keeping cold
starts fast and the Vercel function bundle small.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_PATH = ROOT / "graphrag" / "dataset.json"

TABLES = [
    "patients",
    "care_programs",
    "documents",
    "document_chunks",
    "life_plan_goals",
    "support_plans",
    "daily_notes",
    "goal_progress_events",
    "barriers",
    "interventions",
    "incidents_and_risks",
    "appointments",
    "medications",
    "care_team_members",
    "extracted_entities",
    "extracted_relationships",
    "bottleneck_insights",
    "rag_query_logs",
]


def _clean_value(value: object) -> object:
    """Normalise a single cell into a JSON-serialisable primitive."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    # pandas may surface numpy bool/int/float types; coerce to native Python.
    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, AttributeError):
            pass
    return value


# Normalise legacy provenance labels left over from earlier iterations.
_VALUE_REWRITES = {"seeded_mvp": "seeded_demo"}


def _rewrite(value: object) -> object:
    return _VALUE_REWRITES.get(value, value) if isinstance(value, str) else value


def load_table(name: str) -> list[dict]:
    path = DATA_DIR / f"{name}.xlsx"
    if not path.exists():
        print(f"  ! missing {path.name} (skipping)")
        return []
    frame = pd.read_excel(path, engine="openpyxl")
    records = frame.to_dict(orient="records")
    return [{k: _rewrite(_clean_value(v)) for k, v in row.items()} for row in records]


def main() -> None:
    dataset: dict[str, list[dict]] = {}
    for name in TABLES:
        rows = load_table(name)
        dataset[name] = rows
        print(f"  {name:<28} {len(rows):>4} rows")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\nWrote {OUTPUT_PATH.relative_to(ROOT)} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
