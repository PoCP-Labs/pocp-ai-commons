"""Training contribution evidence validation (Gensyn-aligned draft schema)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from services.evidence import POCP_META_KEY

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "schemas" / "training_contribution_v0.1.yaml"
)
TRAINING_TYPE = "training"
SCHEMA_ID = "pocp.training_contribution.v0.1"


def load_training_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _nested_get(data: dict[str, Any], dotted: str) -> Any:
    parts = dotted.split(".")
    current: Any = data
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def validate_training_evidence(evidence: dict[str, Any] | None) -> dict[str, Any]:
    """Validate training block; returns normalized report or raises ValueError."""
    evidence = evidence or {}
    schema = load_training_schema()
    required = schema.get("required_evidence_fields") or []
    missing: list[str] = []
    for field in required:
        if _nested_get(evidence, field) in (None, ""):
            missing.append(field)

    training = evidence.get("training")
    if not isinstance(training, dict):
        raise ValueError("training contributions require evidence.training object")

    if missing:
        raise ValueError(
            "training evidence missing required fields: " + ", ".join(missing)
        )

    meta = dict(evidence.get(POCP_META_KEY) or {})
    meta["evidence_standard"] = schema.get("schema_id") or SCHEMA_ID
    if "training" not in (meta.get("tags") or []):
        meta["tags"] = list(meta.get("tags") or []) + ["training"]

    return {
        "valid": True,
        "schema_id": schema.get("schema_id") or SCHEMA_ID,
        "job_id": training.get("job_id"),
        "objective": training.get("objective"),
        "dataset_ref": training.get("dataset_ref"),
        "model_ref": training.get("model_ref"),
        "recommended_pocp_meta": meta,
        "finalization_note": (schema.get("finalization") or {}).get(
            "requires_human_or_policy", True
        ),
    }


def enrich_training_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Apply schema tags after validation."""
    report = validate_training_evidence(evidence)
    out = dict(evidence)
    meta = dict(out.get(POCP_META_KEY) or {})
    meta.update(report.get("recommended_pocp_meta") or {})
    out[POCP_META_KEY] = meta
    return out
