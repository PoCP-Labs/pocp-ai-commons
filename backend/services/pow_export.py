"""Export PoCP contribution proof as pow.yaml-compatible interop record.

Maps pocp.contribution_proof.v0.1 → subset aligned with
Proof-of-Contribution Protocol Core (pow.yaml / JSON Schema).

See docs/inspiration-mappings/poc-protocol-core.md
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from services.proof import build_contribution_proof_packet

POW_INTEROP_SCHEMA = "pocp.pow_interop.v0.1"
POW_RECORD_VERSION = "0.1"


def proof_packet_to_pow_record(proof: dict[str, Any]) -> dict[str, Any]:
    """Transform a full PoCP proof packet into a portable pow-style record."""
    event = proof.get("contribution_event") or {}
    evidence = proof.get("evidence") or {}
    entity_block = proof.get("entity_identity") or {}
    primary = entity_block.get("primary") or {}
    finalization = proof.get("finalization") or {}
    conversion = proof.get("contribution_to_rights_conversion") or {}
    integrity = proof.get("integrity") or {}

    return {
        "schema": POW_INTEROP_SCHEMA,
        "pow_version": POW_RECORD_VERSION,
        "contribution_id": event.get("id"),
        "contributor": {
            "entity_id": primary.get("id"),
            "name": primary.get("name"),
            "entity_type": primary.get("entity_type"),
            "owner_id": primary.get("owner_id"),
        },
        "contribution_type": event.get("contribution_type"),
        "description": event.get("description"),
        "status": event.get("status"),
        "created_at": event.get("created_at"),
        "task": event.get("task"),
        "evidence": {
            "content_hash": evidence.get("content_hash"),
            "evidence_types": evidence.get("evidence_types"),
            "provenance": evidence.get("provenance"),
            "items": evidence.get("items"),
        },
        "participants": entity_block.get("participants"),
        "verification": proof.get("verification"),
        "finalization": {
            "mode": finalization.get("mode"),
            "verdict": finalization.get("verdict"),
            "decision_id": finalization.get("decision_id"),
            "finalizer_entity_id": finalization.get("finalizer_entity_id"),
            "policy_id": finalization.get("policy_id"),
            "policy_version": finalization.get("policy_version"),
            "status": finalization.get("status"),
        },
        "rights": {
            "rules_schema": conversion.get("rules_schema"),
            "rules_version": conversion.get("rules_version"),
            "planned_allocations": conversion.get("planned_allocations"),
            "applied_rewards": conversion.get("applied_rewards"),
        },
        "invocation_traces": proof.get("invocation_trace"),
        "integrity": {
            "proof_hash": integrity.get("proof_hash"),
            "evidence_hash": integrity.get("evidence_hash"),
            "pocp_proof_schema": proof.get("proof_schema"),
            "pocp_spec_version": proof.get("spec_version"),
        },
        "interop": {
            "source_inspiration": "github:Gitdigital-products/Proof-of-Contribution-Protocol-Core",
            "note": "Subset of pocp.contribution_proof.v0.1 — not a full pow.yaml replacement.",
        },
    }


def validate_pow_record(record: dict[str, Any]) -> list[str]:
    """Return validation error messages (empty if structurally OK)."""
    errors: list[str] = []
    if record.get("schema") != POW_INTEROP_SCHEMA:
        errors.append(f"schema must be {POW_INTEROP_SCHEMA}")
    if not record.get("contribution_id"):
        errors.append("contribution_id required")
    if not (record.get("contributor") or {}).get("entity_id"):
        errors.append("contributor.entity_id required")
    if not record.get("status"):
        errors.append("status required")
    return errors


def build_pow_export(db: Session, contribution_id: str) -> dict[str, Any]:
    proof = build_contribution_proof_packet(db, contribution_id)
    if proof is None:
        return {"valid": False, "validation_errors": ["contribution not found"], "pow_record": None}
    record = proof_packet_to_pow_record(proof)
    errors = validate_pow_record(record)
    return {
        "valid": len(errors) == 0,
        "validation_errors": errors,
        "pow_record": record,
    }
