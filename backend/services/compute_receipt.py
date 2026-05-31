"""ComputeReceipt — auditable attribution for distributed compute jobs (v0.1)."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

RECEIPT_SPEC = "pocp.compute_receipt.v0.1"
HASH_ALGORITHM = "sha256"


def _stable_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash_material(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_compute_receipt(
    *,
    provider_entity_id: str | None,
    provider_node_id: str | None,
    capability: str,
    adapter: str | None = None,
    model: str | None = None,
    contribution_id: str | None = None,
    task_id: str | None = None,
    job_id: str | None = None,
    initiator_entity_id: str | None = None,
    input_material: str | None = None,
    output_material: str | None = None,
    latency_ms: int | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = started_at or datetime.now(timezone.utc)
    finished = finished_at or datetime.now(timezone.utc)
    started_s = started if isinstance(started, str) else started.isoformat()
    finished_s = finished if isinstance(finished, str) else finished.isoformat()
    input_hash = hash_material(input_material) if input_material else None
    output_hash = hash_material(output_material) if output_material else None

    body = {
        "spec_version": RECEIPT_SPEC,
        "provider_entity_id": provider_entity_id,
        "provider_node_id": provider_node_id or os.getenv("POCP_NODE_ID", "unknown"),
        "capability": capability,
        "adapter": adapter,
        "model": model,
        "contribution_id": contribution_id,
        "task_id": task_id,
        "job_id": job_id,
        "initiator_entity_id": initiator_entity_id,
        "input_hash": input_hash,
        "output_hash": output_hash,
        "latency_ms": latency_ms,
        "started_at": started_s,
        "finished_at": finished_s,
        "extra": extra or {},
    }
    receipt_hash = hash_material(_stable_json({k: v for k, v in body.items() if k != "integrity"}))
    body["integrity"] = {
        "receipt_hash": receipt_hash,
        "hash_algorithm": HASH_ALGORITHM,
    }
    return body


def verify_compute_receipt(receipt: dict[str, Any]) -> bool:
    integrity = receipt.get("integrity") or {}
    expected = integrity.get("receipt_hash")
    if not expected:
        return False
    clone = {k: v for k, v in receipt.items() if k != "integrity"}
    return hash_material(_stable_json(clone)) == expected
