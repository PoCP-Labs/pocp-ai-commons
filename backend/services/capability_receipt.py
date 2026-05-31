"""Capability receipt — per-step proof of Skill/Tool/LLM invocation (pocp.capability_receipt.v0.1).

Embedded in InvocationTrace steps and agent receipts so value-exchange chains
show which capability was invoked, with optional content hashes.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Any

from models.entity import Entity
from models.invocation import InvocationStep

CAPABILITY_RECEIPT_SCHEMA = "pocp.capability_receipt.v0.1"

_ACTION_CAPABILITY_KIND = {
    "uses": "capability",
    "calls": "skill",
    "invokes_llm": "llm",
    "invoke_tool": "tool",
    "invoke_mcp": "tool",
    "invokes_mcp": "tool",
    "invokes_peer_mcp": "tool",
    "reads_dataset": "dataset",
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def infer_capability_kind(action: str) -> str:
    return _ACTION_CAPABILITY_KIND.get(action, "capability")


def capability_endpoint_from_entity(entity: Entity | None) -> str | None:
    if entity is None:
        return None
    meta = entity.metadata_ or {}
    endpoints = meta.get("service_endpoints") or meta.get("endpoints")
    if isinstance(endpoints, list) and endpoints:
        first = endpoints[0]
        return first if isinstance(first, str) else first.get("url")
    if isinstance(endpoints, dict):
        return endpoints.get("url") or endpoints.get("execute")
    mcp = meta.get("mcp_server")
    if isinstance(mcp, dict):
        return mcp.get("url")
    return None


def build_capability_receipt(
    *,
    trace_id: str,
    step: InvocationStep,
    target_entity: Entity | None = None,
    request_summary: str | None = None,
    response_summary: str | None = None,
    duration_ms: int | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a portable capability receipt for one invocation step."""
    step_meta = getattr(step, "metadata_", None) or {}
    merged_extra = {**step_meta, **(extra or {})}
    receipt = {
        "schema": CAPABILITY_RECEIPT_SCHEMA,
        "trace_id": trace_id,
        "step_order": step.step_order,
        "source_entity_id": step.source_entity_id,
        "target_entity_id": step.target_entity_id,
        "action": step.action,
        "capability_kind": infer_capability_kind(step.action),
        "target_entity_type": target_entity.entity_type.value if target_entity else None,
        "target_entity_name": str(target_entity.name) if target_entity else None,
        "endpoint": capability_endpoint_from_entity(target_entity),
        "duration_ms": duration_ms or merged_extra.get("duration_ms"),
        "provider": merged_extra.get("provider"),
        "model": merged_extra.get("model"),
    }
    if request_summary:
        receipt["request_hash"] = _hash_text(request_summary)
        receipt["request_bytes"] = len(request_summary.encode("utf-8"))
    if response_summary:
        receipt["response_hash"] = _hash_text(response_summary)
        receipt["response_bytes"] = len(response_summary.encode("utf-8"))
    if merged_extra:
        receipt["context"] = {k: v for k, v in merged_extra.items() if k not in receipt}
    if merged_extra.get("compute_receipt"):
        receipt["compute_receipt"] = merged_extra["compute_receipt"]
    receipt["receipt_hash"] = compute_capability_receipt_hash(receipt)
    return receipt


def compute_capability_receipt_hash(receipt: dict[str, Any]) -> str:
    payload = {k: v for k, v in receipt.items() if k != "receipt_hash"}
    material = json.dumps(_jsonable(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def build_step_capability_receipts(
    trace_id: str,
    steps: list[InvocationStep],
    entities: dict[str, Entity],
) -> list[dict[str, Any]]:
    return [
        build_capability_receipt(
            trace_id=trace_id,
            step=step,
            target_entity=entities.get(step.target_entity_id),
        )
        for step in steps
    ]
