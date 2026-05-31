"""ComputeArtifact — content-addressed cache for LLM outputs (v0.2 prototype)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from services.compute_receipt import hash_material

# Key: f"{model}:{input_hash}" -> artifact record
_ARTIFACT_STORE: dict[str, dict[str, Any]] = {}


def artifact_cache_enabled() -> bool:
    return os.getenv("POCP_COMPUTE_ARTIFACT_CACHE", "true").lower() in ("1", "true", "yes")


def artifact_key(*, model: str, input_hash: str) -> str:
    return f"{(model or 'default').strip()}:{input_hash}"


def lookup_artifact(*, model: str, input_material: str) -> dict[str, Any] | None:
    if not artifact_cache_enabled():
        return None
    input_hash = hash_material(input_material)
    record = _ARTIFACT_STORE.get(artifact_key(model=model, input_hash=input_hash))
    if not record:
        return None
    return {**record, "input_hash": input_hash}


def store_artifact(
    *,
    model: str,
    input_material: str,
    output_material: str,
    provider_entity_id: str | None = None,
) -> dict[str, Any]:
    input_hash = hash_material(input_material)
    output_hash = hash_material(output_material)
    record = {
        "model": model,
        "input_hash": input_hash,
        "output_hash": output_hash,
        "output_material": output_material,
        "provider_entity_id": provider_entity_id,
        "stored_at": datetime.now(timezone.utc).isoformat(),
    }
    _ARTIFACT_STORE[artifact_key(model=model, input_hash=input_hash)] = record
    return record


def list_artifacts(limit: int = 50) -> list[dict[str, Any]]:
    items = list(_ARTIFACT_STORE.values())
    return items[-limit:]


def clear_artifact_store() -> None:
    _ARTIFACT_STORE.clear()
