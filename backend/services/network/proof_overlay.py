"""Protocol event overlay block for contribution proof packets."""

from __future__ import annotations

from typing import Any

from services.merkle_canonical import (
    MERKLE_ALGORITHM,
    build_inclusion_bundle_unified,
    format_merkle_leaf,
    merkle_root_unified,
    merkle_root_unified_display,
)
from services.network.types import canonical_hash


def step_protocol_event_hash(
    *,
    trace_id: str,
    step_order: int,
    source_entity_id: str,
    target_entity_id: str,
    action: str,
    metadata: dict[str, Any] | None,
) -> str:
    """Deterministic event hash for an invocation step (overlay leaf)."""
    meta = metadata or {}
    return canonical_hash(
        {
            "trace_id": trace_id,
            "step_order": step_order,
            "source_entity_id": source_entity_id,
            "target_entity_id": target_entity_id,
            "action": action,
            "dialogue_id": meta.get("dialogue_id"),
            "dialogue_kind": meta.get("dialogue_kind"),
        }
    )


def build_protocol_event_overlay_block(
    invocations: list[Any],
) -> dict[str, Any] | None:
    """
    Build Merkle overlay for invocation steps linked to a contribution proof.
    Uses the same tree algorithm as ledger_merkle_inclusion.
    """
    leaves: list[dict[str, Any]] = []
    for trace in invocations:
        for step in sorted(trace.steps, key=lambda s: s.step_order):
            event_hash = step_protocol_event_hash(
                trace_id=trace.id,
                step_order=step.step_order,
                source_entity_id=step.source_entity_id,
                target_entity_id=step.target_entity_id,
                action=step.action,
                metadata=step.metadata_,
            )
            leaves.append(
                {
                    "trace_id": trace.id,
                    "step_order": step.step_order,
                    "action": step.action,
                    "event_hash": event_hash,
                    "dialogue_id": (step.metadata_ or {}).get("dialogue_id"),
                }
            )

    if not leaves:
        return None

    hashes = [item["event_hash"] for item in leaves]
    root_hex = merkle_root_unified(hashes)
    inclusions = []
    for item in leaves:
        bundle = build_inclusion_bundle_unified(hashes, item["event_hash"])
        if bundle:
            inclusions.append(
                {
                    "trace_id": item["trace_id"],
                    "step_order": item["step_order"],
                    "dialogue_id": item["dialogue_id"],
                    "inclusion": bundle,
                }
            )

    return {
        "schema": "pocp.protocol_event_overlay.v0.1",
        "merkle_algorithm": MERKLE_ALGORITHM,
        "merkle_root": root_hex,
        "merkle_root_display": merkle_root_unified_display(hashes),
        "leaf_count": len(leaves),
        "leaves": leaves,
        "inclusions": inclusions,
        "ledger_compatible": True,
        "note": "Same sha256-pair-concat-v0.1 as ledger_merkle_inclusion; event_hash leaves use sha256: display prefix.",
    }
