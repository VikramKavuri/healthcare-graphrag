"""Load the synthetic healthcare dataset from the committed JSON snapshot.

The runtime depends only on the Python standard library here. The Excel source
files are converted to ``dataset.json`` at build time by
``scripts/prepare_data.py`` (which is the only place pandas/openpyxl are used).
This keeps cold starts fast and the serverless bundle small.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

Row = dict[str, object]
Table = list[Row]
Dataset = dict[str, Table]

DATASET_PATH = Path(__file__).resolve().parent / "dataset.json"

TABLE_NAMES = (
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
)


@lru_cache(maxsize=1)
def load_dataset() -> Dataset:
    """Load every table from the JSON snapshot (cached for the process lifetime)."""
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset snapshot not found at {DATASET_PATH}. "
            "Run `python scripts/prepare_data.py` to generate it."
        )
    with DATASET_PATH.open(encoding="utf-8") as fh:
        raw: Dataset = json.load(fh)
    # Guarantee every expected table exists, even if empty.
    return {name: raw.get(name, []) for name in TABLE_NAMES}


def get_table(name: str) -> Table:
    """Return a single table by name (empty list if absent)."""
    return load_dataset().get(name, [])
