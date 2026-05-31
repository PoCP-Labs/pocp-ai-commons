"""IntelReceipt — auditable attribution for intelligence-layer services (v0.2)."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

INTEL_RECEIPT_SPEC = "pocp.intel_receipt.v0.2"
HASH_ALGORITHM = "sha256"


def _stable_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_intel_receipt(
    *,
    provider_entity_id: str,
    service: str,
    intel_units: int = 1,
    intel_equivalent_tokens: int | None = None,
    contribution_id: str | None = None,
    task_id: str | None = None,
    initiator_entity_id: str | None = None,
    downstream_compute_receipt_hashes: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from services.compute_metering import intel_usage_for_service

    usage = intel_usage_for_service(service)
    eq = intel_equivalent_tokens if intel_equivalent_tokens is not None else int(
        usage.get("intel_equivalent_tokens") or 1000
    )
    body = {
        "spec_version": INTEL_RECEIPT_SPEC,
        "provider_entity_id": provider_entity_id,
        "provider_node_id": os.getenv("POCP_NODE_ID", "unknown"),
        "service": service,
        "intel_units": intel_units,
        "intel_equivalent_tokens": eq,
        "contribution_id": contribution_id,
        "task_id": task_id,
        "initiator_entity_id": initiator_entity_id,
        "downstream_compute_receipt_hashes": downstream_compute_receipt_hashes or [],
        "usage": {**usage, "intel_units": intel_units, "intel_equivalent_tokens": eq},
        "extra": extra or {},
    }
    receipt_hash = _hash(_stable_json({k: v for k, v in body.items() if k != "integrity"}))
    body["integrity"] = {"receipt_hash": receipt_hash, "hash_algorithm": HASH_ALGORITHM}
    return body


def verify_intel_receipt(receipt: dict[str, Any]) -> bool:
    integrity = receipt.get("integrity") or {}
    expected = integrity.get("receipt_hash")
    if not expected:
        return False
    clone = {k: v for k, v in receipt.items() if k != "integrity"}
    return _hash(_stable_json(clone)) == expected
