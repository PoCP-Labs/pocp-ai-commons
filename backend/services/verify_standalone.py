"""Standalone verification — verify ledger and proofs without trusting the operator.

Inspired by Bitcoin full-node audit: anyone can recompute hashes and confirm history.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from services.crypto_suite import verify_federation_signatures
from services.federation_crypto import verify_message
from services.anchor_cosign import verify_anchor_attestations
from services.graph_merkle import verify_graph_merkle_inclusion
from services.ledger_merkle import merkle_root, verify_merkle_inclusion
from services.ledger_chain import verify_ledger_records
from services.proof import compute_contribution_proof_hash


def _http_get_json(url: str, timeout: float = 15.0) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def verify_ledger_export(export: dict[str, Any]) -> dict[str, Any]:
    """Verify an exported ledger bundle from GET /api/v1/ledger/export."""
    records = export.get("records") or []
    chain = verify_ledger_records(records)
    hashes = [r["record_hash"] for r in records if r.get("record_hash")]
    return {
        **chain,
        "merkle_root": merkle_root(hashes) if hashes else None,
        "spec_version": export.get("spec_version"),
        "export_valid": chain["valid"],
    }


def verify_proof_integrity(
    proof: dict[str, Any],
    *,
    trusted_public_key: str | None = None,
    require_signature: bool = False,
) -> dict[str, Any]:
    """Verify proof hash, embedded ledger subchain, and optional federation signature."""
    if proof.get("proof_type") == "pocp_exchange_proof":
        from services.exchange_proof import verify_exchange_proof_integrity

        return verify_exchange_proof_integrity(
            proof,
            trusted_public_key=trusted_public_key,
            require_signature=require_signature,
        )

    checks: list[dict[str, Any]] = []
    valid = True

    integrity = proof.get("integrity") or {}
    declared_hash = integrity.get("proof_hash")
    computed_hash = compute_contribution_proof_hash(proof)
    hash_ok = bool(declared_hash) and declared_hash == computed_hash
    checks.append(
        {
            "check": "proof_hash",
            "valid": hash_ok,
            "declared": declared_hash,
            "computed": computed_hash,
        }
    )
    valid = valid and hash_ok

    ledger_audit = proof.get("ledger_audit") or {}
    audit_records = ledger_audit.get("records") or []
    chain = verify_ledger_records(audit_records) if audit_records else {
        "valid": True,
        "count": 0,
        "tip_hash": None,
        "genesis_hash": None,
    }
    tip_declared = integrity.get("ledger_tip_hash")
    tip_matches = tip_declared == chain.get("tip_hash") if audit_records else tip_declared is None
    checks.append(
        {
            "check": "ledger_subchain",
            "valid": chain["valid"] and tip_matches,
            "record_count": chain.get("count", 0),
            "tip_hash": chain.get("tip_hash"),
            "tip_matches_integrity": tip_matches,
        }
    )
    valid = valid and chain["valid"] and tip_matches

    record_hashes = ledger_audit.get("record_hashes") or []
    if record_hashes and chain.get("tip_hash") and record_hashes[-1] != chain["tip_hash"]:
        checks.append(
            {
                "check": "record_hashes_tip",
                "valid": False,
                "expected": chain["tip_hash"],
                "actual": record_hashes[-1],
            }
        )
        valid = False
    else:
        checks.append({"check": "record_hashes_tip", "valid": True})

    federation = proof.get("federation") or {}
    signatures = federation.get("signatures") or {}
    classic = signatures.get("classic") or {}
    signature = federation.get("signature") or classic.get("signature")
    sig_valid: bool | None = None
    if signature and declared_hash:
        try:
            if federation.get("signatures"):
                verify_federation_signatures(
                    federation,
                    declared_hash,
                    trusted_classic_key=trusted_public_key,
                    trusted_pqc_key=None,
                )
            elif trusted_public_key:
                sig_valid = verify_message(declared_hash, signature, trusted_public_key)
            else:
                sig_valid = None
            if sig_valid is not False:
                checks.append({"check": "federation_signature", "valid": True, "signed": True})
            else:
                checks.append({"check": "federation_signature", "valid": False, "signed": True})
                valid = False
        except Exception as exc:
            checks.append(
                {
                    "check": "federation_signature",
                    "valid": False,
                    "signed": True,
                    "error": str(exc),
                }
            )
            valid = False
    elif require_signature:
        checks.append({"check": "federation_signature", "valid": False, "signed": False})
        valid = False
    else:
        checks.append({"check": "federation_signature", "valid": True, "signed": False, "skipped": True})

    finalization = proof.get("finalization") or {}
    entity_finalizations = (proof.get("verification") or {}).get("entity_finalizations") or []
    human_reviews = (proof.get("verification") or {}).get("human_reviews") or []
    has_finalization = bool(
        finalization.get("finalizer_entity_id")
        or any(r.get("approved") for r in entity_finalizations)
        or any(r.get("approved") for r in human_reviews)
        or proof.get("contribution_event", {}).get("status") == "approved"
    )
    checks.append({"check": "entity_finalization_present", "valid": has_finalization, "optional": False})
    if not has_finalization:
        valid = False

    inclusion = proof.get("ledger_merkle_inclusion")
    if inclusion and inclusion.get("leaf_hash"):
        merkle_ok = verify_merkle_inclusion(
            inclusion["leaf_hash"],
            inclusion.get("merkle_proof") or [],
            inclusion.get("merkle_root") or "",
        )
        checks.append(
            {
                "check": "ledger_merkle_inclusion",
                "valid": merkle_ok,
                "leaf_index": inclusion.get("leaf_index"),
                "tree_size": inclusion.get("tree_size"),
                "merkle_root": inclusion.get("merkle_root"),
            }
        )
        valid = valid and merkle_ok

    graph_inclusion = proof.get("graph_merkle_inclusion")
    if graph_inclusion and graph_inclusion.get("proofs"):
        graph_ok = verify_graph_merkle_inclusion(graph_inclusion)
        checks.append(
            {
                "check": "graph_merkle_inclusion",
                "valid": graph_ok,
                "edge_count": graph_inclusion.get("edge_count"),
                "tree_size": graph_inclusion.get("tree_size"),
                "graph_merkle_root": graph_inclusion.get("merkle_root"),
            }
        )
        valid = valid and graph_ok

    return {
        "valid": valid,
        "proof_id": proof.get("proof_id"),
        "contribution_id": (proof.get("contribution_event") or {}).get("id"),
        "checks": checks,
        "ledger_subchain": chain,
    }


def audit_remote_node(base_url: str, *, timeout: float = 15.0) -> dict[str, Any]:
    """Fetch and cross-check a node's public verify + anchor endpoints (no DB trust)."""
    root = base_url.rstrip("/")
    result: dict[str, Any] = {"base_url": root, "valid": False, "checks": []}
    try:
        verify = _http_get_json(f"{root}/api/v1/ledger/verify", timeout=timeout)
        anchor = _http_get_json(f"{root}/api/v1/ledger/anchor", timeout=timeout)
    except urllib.error.URLError as exc:
        result["error"] = str(exc.reason if hasattr(exc, "reason") else exc)
        return result

    chain_ok = bool(verify.get("valid"))
    result["checks"].append({"check": "ledger_verify", "valid": chain_ok, "detail": verify})

    anchor_ok = bool(anchor.get("ledger_valid"))
    tip_matches = verify.get("tip_hash") == anchor.get("tip_hash")
    merkle_ok = anchor.get("merkle_root") is not None
    graph_merkle_ok = anchor.get("graph_merkle_root") is not None
    result["checks"].append(
        {
            "check": "anchor_graph_merkle_present",
            "valid": graph_merkle_ok,
            "graph_merkle_root": anchor.get("graph_merkle_root"),
            "graph_edge_count": anchor.get("graph_edge_count"),
        }
    )
    result["checks"].append(
        {
            "check": "anchor_ledger_valid",
            "valid": anchor_ok,
            "ledger_valid": anchor.get("ledger_valid"),
        }
    )
    result["checks"].append(
        {
            "check": "anchor_tip_matches_verify",
            "valid": tip_matches,
            "verify_tip": verify.get("tip_hash"),
            "anchor_tip": anchor.get("tip_hash"),
        }
    )
    result["checks"].append(
        {
            "check": "anchor_merkle_present",
            "valid": merkle_ok,
            "merkle_root": anchor.get("merkle_root"),
            "record_count": anchor.get("record_count"),
        }
    )

    node_info: dict[str, Any] | None = None
    try:
        node_info = _http_get_json(f"{root}/api/v1/federation/node", timeout=timeout)
        result["node_id"] = node_info.get("node_id")
    except urllib.error.URLError:
        node_info = None

    result["verify"] = verify
    result["anchor"] = anchor
    result["node"] = node_info

    try:
        wallet_audit = _http_get_json(f"{root}/api/v1/wallets/audit", timeout=timeout)
        wallet_ok = bool(wallet_audit.get("valid"))
        result["checks"].append(
            {
                "check": "wallet_transaction_replay",
                "valid": wallet_ok,
                "wallet_count": wallet_audit.get("wallet_count"),
                "invalid_count": wallet_audit.get("invalid_count"),
            }
        )
        result["wallet_audit"] = wallet_audit
    except urllib.error.URLError:
        result["checks"].append(
            {"check": "wallet_transaction_replay", "valid": True, "skipped": True}
        )

    wallet_check = next(
        (c for c in result["checks"] if c.get("check") == "wallet_transaction_replay"),
        {"valid": True},
    )
    cosign = verify_anchor_attestations(anchor)
    if cosign.get("attestation_count"):
        result["checks"].append(
            {
                "check": "anchor_peer_attestations",
                "valid": cosign.get("valid"),
                "attestation_count": cosign.get("attestation_count"),
                "valid_count": cosign.get("valid_count"),
            }
        )
        result["cosign"] = cosign
    cosign_ok = cosign.get("valid", True)
    result["valid"] = (
        chain_ok
        and anchor_ok
        and tip_matches
        and merkle_ok
        and graph_merkle_ok
        and wallet_check.get("valid", True)
        and cosign_ok
    )
    return result
