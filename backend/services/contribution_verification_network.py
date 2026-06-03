"""CI-8 verification network — verifier_node entity wiring and standalone API helpers."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity, EntityStatus, EntityType
from services.entity.schemas import LOCAL_VERIFIER_NODE_ID

VERIFICATION_NETWORK_SPEC = "pocp-verification-network-v0.1"


def _backend_url() -> str:
    return os.getenv("BACKEND_URL", "http://127.0.0.1:8008").rstrip("/")


def resolve_verifier_node(
    db: Session,
    *,
    entity_id: str | None = None,
) -> dict[str, Any] | None:
    """Resolve an active verifier_node entity and its service endpoints."""
    target_id = entity_id or LOCAL_VERIFIER_NODE_ID
    entity = db.get(Entity, target_id)
    if entity is None or entity.entity_type != EntityType.verifier_node:
        return None
    if entity.status != EntityStatus.active:
        return None

    meta = entity.metadata_ or {}
    endpoints = dict(meta.get("service_endpoints") or {})
    backend = _backend_url()
    endpoints.setdefault("witness", f"{backend}/api/v1/intelligence/compute/witness")
    endpoints.setdefault("network", f"{backend}/api/v1/verification/network")
    endpoints.setdefault("manifest", f"{backend}/api/v1/verification/verifier-node/{entity.id}")
    endpoints.setdefault("challenge", f"{backend}/api/v1/contributions/{{contribution_id}}/challenge")
    endpoints.setdefault("appeal", f"{backend}/api/v1/contributions/{{contribution_id}}/appeal")
    endpoints.setdefault("resolve_dispute", f"{backend}/api/v1/contributions/{{contribution_id}}/resolve-dispute")
    endpoints.setdefault("proof_verify", f"{backend}/api/v1/verification/proof/verify")

    return {
        "entity_id": entity.id,
        "entity_type": entity.entity_type.value,
        "display_name": entity.name,
        "verifier_kinds": list(meta.get("verifier_kinds") or ["ai_review"]),
        "trust_level": meta.get("trust_level", "standard"),
        "service_endpoints": endpoints,
        "owner_id": entity.owner_id,
    }


def attach_verifier_node(
    consensus: dict[str, Any],
    verifier_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    """Annotate multi-verifier consensus with the accountable verifier_node."""
    if verifier_snapshot is None:
        return consensus
    consensus = dict(consensus)
    consensus["verifier_node"] = verifier_snapshot
    consensus["verifier_node_id"] = verifier_snapshot["entity_id"]
    return consensus


def build_verification_network_manifest(db: Session) -> dict[str, Any]:
    """Sketch manifest for standalone verifier nodes (Phase A → Phase B ``pocp-node``)."""
    backend = _backend_url()
    verifier = resolve_verifier_node(db) or {
        "entity_id": LOCAL_VERIFIER_NODE_ID,
        "entity_type": "verifier_node",
        "display_name": "Local Verifier Node (unregistered)",
        "verifier_kinds": ["ai_review", "peer_witness"],
        "trust_level": "standard",
        "service_endpoints": {
            "network": f"{backend}/api/v1/verification/network",
            "manifest": f"{backend}/api/v1/verification/verifier-node",
        },
    }

    return {
        "spec": VERIFICATION_NETWORK_SPEC,
        "principle": "AI advisory + accountable dispute resolution; no single-LLM final approval",
        "default_verifier_node_id": LOCAL_VERIFIER_NODE_ID,
        "verifier_node": verifier,
        "dispute_lifecycle": ["challenge", "appeal", "resolve-dispute"],
        "endpoints": {
            "network": f"{backend}/api/v1/verification/network",
            "verifier_manifest": f"{backend}/api/v1/verification/verifier-node",
            "verifier_manifest_by_id": f"{backend}/api/v1/verification/verifier-node/{{entity_id}}",
            "proof_verify": f"{backend}/api/v1/verification/proof/verify",
            "dispute_evidence_digest": f"{backend}/api/v1/verification/disputes/evidence/digest",
            "contribution_challenge": f"{backend}/api/v1/contributions/{{contribution_id}}/challenge",
            "contribution_appeal": f"{backend}/api/v1/contributions/{{contribution_id}}/appeal",
            "contribution_resolve": f"{backend}/api/v1/contributions/{{contribution_id}}/resolve-dispute",
            "ledger_verify": f"{backend}/api/v1/ledger/verify",
        },
        "advisory_entity_types": ["llm", "agent", "verifier_node"],
    }
