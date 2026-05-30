"""Federation intelligence — cross-node contribution intelligence packets."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from intelligence.engines import build_intelligence_packet
from services.proof import build_contribution_proof_packet


def export_federation_intelligence_packet(
    db: Session,
    contribution_id: str,
    *,
    node_id: str | None = None,
) -> dict[str, Any] | None:
    """Portable intelligence + proof bundle for trusted federation peers."""
    intelligence = build_intelligence_packet(db, contribution_id)
    if intelligence is None:
        return None

    proof = build_contribution_proof_packet(db, contribution_id)
    node = node_id or os.getenv("POCP_NODE_ID", "pocp-node-local")

    invocation_trace = proof.get("invocation_trace") if proof else None
    finalization = proof.get("finalization") if proof else None
    proof_hash = (proof.get("integrity") or {}).get("proof_hash") if proof else None

    return {
        "export_type": "pocp_federation_intelligence_v0.2",
        "source_node_id": node,
        "contribution_id": contribution_id,
        "intelligence_packet": intelligence,
        "contribution_proof": proof,
        "invocation_trace": invocation_trace,
        "finalization": finalization,
        "proof_hash": proof_hash,
        "advisory_only": True,
        "traceable_finalization": True,
        "principle": "Everything connects through verified contribution.",
    }


def summarize_federation_ingest(packet: dict[str, Any]) -> dict[str, Any]:
    """Advisory summary when receiving a federation intelligence packet (no import)."""
    intel = packet.get("intelligence_packet") or {}
    proof = packet.get("contribution_proof") or {}
    finalization = packet.get("finalization") or proof.get("finalization") or {}
    invocation = packet.get("invocation_trace") or proof.get("invocation_trace") or {}
    return {
        "source_node_id": packet.get("source_node_id"),
        "contribution_id": packet.get("contribution_id"),
        "export_type": packet.get("export_type"),
        "status": intel.get("status"),
        "participant_count": len(intel.get("participants") or []),
        "proof_hash": packet.get("proof_hash") or (proof.get("integrity") or {}).get("proof_hash"),
        "finalization_mode": finalization.get("mode"),
        "finalizer_entity_id": finalization.get("finalizer_entity_id"),
        "invocation_trace_count": invocation.get("trace_count"),
        "advisory_only": True,
        "recommended_action": "Validate proof hash, then POST /api/v1/federation/import-proof if trusted.",
    }


def protocol_excerpt_from_bundle(
    proof: dict,
    intelligence_bundle: dict | None = None,
) -> dict[str, Any]:
    """Extract portable protocol fields to store on FederatedImport.payload."""
    excerpt: dict[str, Any] = {
        "proof_hash": (proof.get("integrity") or {}).get("proof_hash"),
        "invocation_trace": proof.get("invocation_trace"),
        "finalization": proof.get("finalization"),
    }
    if intelligence_bundle:
        excerpt["intelligence_export_type"] = intelligence_bundle.get("export_type")
        intel = intelligence_bundle.get("intelligence_packet") or {}
        excerpt["verification_summary"] = intel.get("verification")
        excerpt["reward_advisory"] = intel.get("reward_advisory")
    return excerpt
