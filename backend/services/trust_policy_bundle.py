"""Trust Policy Bundle — federation trust + finalization + import validation rules."""

from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from fastapi import HTTPException

from intelligence.entity_ontology import (
    ENTITY_CONNECTION_SCHEMA,
    role_fits_entity_type,
    validate_invocation_edge,
    validate_participant_role,
)

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "trust_policy_bundle.yaml"
TRUST_POLICY_BUNDLE_SCHEMA = "pocp.trust_policy_bundle.v0.1"
CAPABILITY_RECEIPT_SCHEMA = "pocp.capability_receipt.v0.1"


@lru_cache(maxsize=1)
def _load_bundle_config() -> dict[str, Any]:
    if not _CONFIG_PATH.exists():
        return {
            "spec_version": "0.1",
            "bundle_id": "pocp_trust_policy_v1",
            "import_rules": {},
        }
    with _CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def clear_trust_policy_bundle_cache() -> None:
    _load_bundle_config.cache_clear()


def import_rules() -> dict[str, Any]:
    return dict(_load_bundle_config().get("import_rules") or {})


def _strict_mode() -> bool:
    return os.getenv("POCP_STRICT_TRUST_POLICY", "false").lower() in ("true", "1", "yes", "on")


def bundle_fingerprint() -> str:
    cfg = _load_bundle_config()
    material = json.dumps(
        {"bundle_id": cfg.get("bundle_id"), "import_rules": cfg.get("import_rules") or {}},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def trust_policy_bundle_manifest() -> dict[str, Any]:
    """Portable bundle for federation peers — trust, finalization, connections, import rules."""
    from services.finalization import finalization_policy_manifest
    from services.rights_conversion import rights_rules_manifest
    from services.trust_config import (
        canonical_trust_payload,
        load_trusted_nodes,
        trust_list_hash,
        trusted_nodes_source,
    )
    from intelligence.entity_ontology import connection_matrix_document

    cfg = _load_bundle_config()
    rules = import_rules()
    return {
        "schema": TRUST_POLICY_BUNDLE_SCHEMA,
        "spec_version": cfg.get("spec_version", "0.1"),
        "bundle_id": cfg.get("bundle_id", "pocp_trust_policy_v1"),
        "bundle_fingerprint": bundle_fingerprint(),
        "strict_mode_env": "POCP_STRICT_TRUST_POLICY",
        "strict_mode_active": _strict_mode(),
        "import_rules": rules,
        "federation_trust": {
            "trusted_node_count": len(load_trusted_nodes()),
            "trusted_nodes": canonical_trust_payload(),
            "trust_list_hash": trust_list_hash(),
            "source": trusted_nodes_source(),
        },
        "finalization_policy": finalization_policy_manifest(),
        "entity_connections": {
            "schema": ENTITY_CONNECTION_SCHEMA,
            "matrix": connection_matrix_document(),
        },
        "rights_rules": rights_rules_manifest(),
        "docs": "docs/protocol/TRUST-POLICY-BUNDLE.md",
        "validate_api": "POST /api/v1/federation/validate-proof",
    }


def _check(
    check_id: str,
    ok: bool,
    *,
    detail: str | None = None,
    blocking: bool = False,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "ok": ok,
        "blocking": blocking,
        "detail": detail,
    }


def _entity_type_map_from_proof(proof: dict) -> dict[str, str]:
    mapping: dict[str, str] = {}
    identity = proof.get("entity_identity") or {}
    primary = identity.get("primary")
    if isinstance(primary, dict) and primary.get("id") and primary.get("entity_type"):
        mapping[primary["id"]] = primary["entity_type"]
    for item in identity.get("participants") or []:
        entity = item.get("entity") or {}
        if entity.get("id") and entity.get("entity_type"):
            mapping[entity["id"]] = entity["entity_type"]
    graph = proof.get("contribution_graph") or {}
    for node in graph.get("nodes") or []:
        if node.get("id") and node.get("entity_type"):
            mapping.setdefault(node["id"], node["entity_type"])
    return mapping


def validate_proof_against_trust_policy(
    proof: dict,
    *,
    source_node_id: str | None = None,
    raise_on_block: bool = True,
) -> dict[str, Any]:
    """Validate a contribution proof packet against the active trust policy bundle."""
    rules = import_rules()
    strict = _strict_mode() or bool(rules.get("enforce_invocation_matrix_strict"))
    checks: list[dict[str, Any]] = []

    expected_type = rules.get("proof_type", "pocp_contribution_proof")
    checks.append(
        _check(
            "proof_type",
            proof.get("proof_type") == expected_type,
            detail=f"expected {expected_type}, got {proof.get('proof_type')!r}",
            blocking=True,
        )
    )

    event = proof.get("contribution_event") or {}
    allowed_statuses = rules.get("allowed_contribution_statuses") or ["approved"]
    status = event.get("status")
    checks.append(
        _check(
            "contribution_status",
            status in allowed_statuses,
            detail=f"status {status!r} not in {allowed_statuses}",
            blocking=True,
        )
    )

    if rules.get("require_integrity_proof_hash", True):
        proof_hash = (proof.get("integrity") or {}).get("proof_hash")
        checks.append(
            _check(
                "integrity_proof_hash",
                bool(proof_hash),
                detail="missing integrity.proof_hash",
                blocking=True,
            )
        )

    if rules.get("require_evidence_content_hash", True):
        content_hash = (proof.get("evidence") or {}).get("content_hash")
        checks.append(
            _check(
                "evidence_content_hash",
                bool(content_hash),
                detail="missing evidence.content_hash",
                blocking=True,
            )
        )

    min_witnesses = int(rules.get("min_witness_count") or 0)
    if min_witnesses > 0:
        witnesses = (proof.get("verification") or {}).get("ai_advisory") or []
        checks.append(
            _check(
                "min_witness_count",
                len(witnesses) >= min_witnesses,
                detail=f"need {min_witnesses} witnesses, got {len(witnesses)}",
                blocking=True,
            )
        )

    if rules.get("validate_participant_roles", True):
        for item in (proof.get("entity_identity") or {}).get("participants") or []:
            role = item.get("role")
            entity = item.get("entity") or {}
            et = entity.get("entity_type")
            role_ok = True
            detail = None
            if role:
                try:
                    validate_participant_role(role)
                except ValueError:
                    role_ok = False
                    detail = f"unknown role {role!r}"
                if role_ok and et and not role_fits_entity_type(role, et):
                    role_ok = False
                    detail = f"role {role!r} does not fit entity_type {et!r}"
            checks.append(
                _check(
                    f"participant_role:{role}:{entity.get('id', 'unknown')}",
                    role_ok,
                    detail=detail,
                    blocking=strict,
                )
            )

    if rules.get("validate_invocation_edges", True):
        type_map = _entity_type_map_from_proof(proof)
        traces = (proof.get("invocation_trace") or {}).get("traces") or []
        for trace in traces:
            trace_id = trace.get("id", "unknown")
            for step in trace.get("steps") or []:
                src_id = step.get("source_entity_id")
                tgt_id = step.get("target_entity_id")
                action = step.get("action")
                src_type = type_map.get(src_id)
                tgt_type = type_map.get(tgt_id)
                if not src_type or not tgt_type or not action:
                    checks.append(
                        _check(
                            f"invocation_step_types:{trace_id}:{step.get('step_order')}",
                            not strict,
                            detail="missing entity types or action for invocation step",
                            blocking=strict,
                        )
                    )
                    continue
                edge = validate_invocation_edge(src_type, tgt_type, action, strict=False)
                checks.append(
                    _check(
                        f"invocation_edge:{src_type}->{tgt_type}",
                        edge["ok"],
                        detail=(
                            None
                            if edge["ok"]
                            else f"expected action {edge['expected_action']!r}, got {action!r}"
                        ),
                        blocking=strict,
                    )
                )

    if rules.get("require_capability_receipt_on_steps", False):
        traces = (proof.get("invocation_trace") or {}).get("traces") or []
        for trace in traces:
            receipts = trace.get("capability_receipts") or []
            steps = trace.get("steps") or []
            if len(receipts) < len(steps):
                checks.append(
                    _check(
                        f"capability_receipts:{trace.get('id', 'unknown')}",
                        False,
                        detail="fewer capability_receipts than invocation steps",
                        blocking=True,
                    )
                )
            for step in steps:
                meta = step.get("metadata") or {}
                receipt = meta.get("capability_receipt") or {}
                schema = receipt.get("schema")
                checks.append(
                    _check(
                        f"step_receipt:{trace.get('id')}:{step.get('step_order')}",
                        schema == CAPABILITY_RECEIPT_SCHEMA,
                        detail=f"step metadata missing {CAPABILITY_RECEIPT_SCHEMA}",
                        blocking=True,
                    )
                )

    failed = [c for c in checks if not c["ok"]]
    blocking_failures = [c for c in failed if c.get("blocking")]

    result = {
        "schema": TRUST_POLICY_BUNDLE_SCHEMA,
        "bundle_id": _load_bundle_config().get("bundle_id"),
        "bundle_fingerprint": bundle_fingerprint(),
        "source_node_id": source_node_id,
        "valid": len(failed) == 0,
        "blocking_valid": len(blocking_failures) == 0,
        "check_count": len(checks),
        "failed_count": len(failed),
        "blocking_failed_count": len(blocking_failures),
        "checks": checks,
    }

    if raise_on_block and blocking_failures:
        first = blocking_failures[0]
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Proof failed trust policy validation",
                "check_id": first["id"],
                "detail": first.get("detail"),
                "bundle_fingerprint": result["bundle_fingerprint"],
            },
        )

    return result
