"""PoCP crypto agility — suite registry, hybrid signatures, quantum-readiness policy.

Classic v0.1: SHA-256 + Ed25519 (legacy).
Hybrid v0.2: SHA-256 + Ed25519 + ML-DSA-65 (federation default when PQC keys set).
Hash v0.3: SHA-3-256 + hybrid signatures (new ledger rows).

PQC uses liboqs-python when installed; otherwise dev stub for wire-format testing.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException

from services.federation_crypto import get_node_public_key_hex, sign_message, verify_message
from services.pqc_dsa import (
    PQC_SIG_DEV_STUB,
    PQC_SIG_TARGET,
    get_pqc_public_key_hex,
    pqc_implementation_status,
    sign_pqc,
    verify_pqc,
)

SUITE_V01_CLASSIC = "pocp-crypto-v0.1-classic"
SUITE_V02_HYBRID = "pocp-crypto-v0.2-hybrid"
SUITE_V03_HASH = "pocp-crypto-v0.3-hash"

CLASSIC_SIG = "ed25519"
DEFAULT_HASH = "sha256"
SHA3_HASH = "sha3-256"
SUPPORTED_HASHES = frozenset({DEFAULT_HASH, SHA3_HASH})

_SUITE_SPECS: dict[str, dict[str, Any]] = {
    SUITE_V01_CLASSIC: {
        "hash_algorithm": DEFAULT_HASH,
        "signature_algorithms": [CLASSIC_SIG],
        "hybrid": False,
        "quantum_status": "classic_only",
        "quantum_threat": "Ed25519 vulnerable to Shor; SHA-256 reduced margin under Grover",
        "recommended_for": "legacy_nodes_and_transition",
    },
    SUITE_V02_HYBRID: {
        "hash_algorithm": DEFAULT_HASH,
        "signature_algorithms": [CLASSIC_SIG, PQC_SIG_TARGET],
        "hybrid": True,
        "quantum_status": "hybrid_transition",
        "quantum_threat": "Classic leg deprecated when PQC leg verified; migrate anchors",
        "recommended_for": "new_federation_nodes_and_high_value_proofs",
    },
    SUITE_V03_HASH: {
        "hash_algorithm": SHA3_HASH,
        "signature_algorithms": [CLASSIC_SIG, PQC_SIG_TARGET],
        "hybrid": True,
        "quantum_status": "hash_and_signature_transition",
        "quantum_threat": "SHA-3 for new chain rows; PQC signatures required",
        "recommended_for": "new_ledger_records_post_2028",
    },
}


def active_crypto_suite() -> str:
    env = os.getenv("POCP_CRYPTO_SUITE", "").strip()
    if env:
        return env
    if get_pqc_public_key_hex():
        return SUITE_V02_HYBRID
    return SUITE_V01_CLASSIC


def active_hash_algorithm() -> str:
    return suite_spec(active_crypto_suite())["hash_algorithm"]


def minimum_accepted_crypto_suite() -> str:
    return os.getenv("POCP_MIN_CRYPTO_SUITE", SUITE_V01_CLASSIC).strip() or SUITE_V01_CLASSIC


def require_pqc_signature() -> bool:
    return os.getenv("POCP_REQUIRE_PQC_SIGNATURE", "false").lower() == "true"


def suite_spec(suite_id: str | None = None) -> dict[str, Any]:
    sid = suite_id or active_crypto_suite()
    spec = _SUITE_SPECS.get(sid)
    if spec is None:
        raise ValueError(f"Unknown crypto suite: {sid}")
    return {"suite_id": sid, **spec}


def list_crypto_suites() -> list[dict[str, Any]]:
    return [suite_spec(sid) for sid in _SUITE_SPECS]


def _suite_rank(suite_id: str) -> int:
    order = [SUITE_V01_CLASSIC, SUITE_V02_HYBRID, SUITE_V03_HASH]
    try:
        return order.index(suite_id)
    except ValueError:
        return -1


def suite_meets_minimum(suite_id: str, minimum: str | None = None) -> bool:
    return _suite_rank(suite_id) >= _suite_rank(minimum or minimum_accepted_crypto_suite())


def hash_digest(message: str, algorithm: str = DEFAULT_HASH) -> str:
    import hashlib

    if algorithm not in SUPPORTED_HASHES:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    if algorithm == SHA3_HASH:
        return hashlib.sha3_256(message.encode("utf-8")).hexdigest()
    return hashlib.sha256(message.encode("utf-8")).hexdigest()


def get_node_pqc_public_key_hex() -> str | None:
    return get_pqc_public_key_hex()


def build_signature_block(
    message: str,
    *,
    node_id: str | None = None,
    signed_field: str,
    suite_id: str | None = None,
) -> dict[str, Any] | None:
    """Build federation signature metadata for proofs, anchors, and imports."""
    suite = suite_id or active_crypto_suite()
    spec = suite_spec(suite)
    classic_pub = get_node_public_key_hex()
    classic_sig = sign_message(message) if classic_pub else None
    if not classic_pub or not classic_sig:
        return None

    block: dict[str, Any] = {
        "node_id": node_id or os.getenv("POCP_NODE_ID", "unknown"),
        "crypto_suite": suite,
        "signed_field": signed_field,
        "public_key": classic_pub,
        "signature": classic_sig,
        "signatures": {
            "classic": {
                "algorithm": CLASSIC_SIG,
                "public_key": classic_pub,
                "signature": classic_sig,
            }
        },
    }

    if spec.get("hybrid"):
        pqc_result = sign_pqc(message)
        if pqc_result:
            algorithm, pqc_pub, pqc_sig = pqc_result
            impl = "liboqs" if algorithm == PQC_SIG_TARGET else "dev-stub"
            block["signatures"]["pqc"] = {
                "algorithm": algorithm,
                "target_algorithm": PQC_SIG_TARGET,
                "public_key": pqc_pub,
                "signature": pqc_sig,
                "implementation": impl,
            }

    return block


def _extract_classic(federation: dict[str, Any]) -> tuple[str, str, str]:
    signatures = federation.get("signatures") or {}
    classic = signatures.get("classic") or {}
    algorithm = classic.get("algorithm") or CLASSIC_SIG
    public_key = classic.get("public_key") or federation.get("public_key")
    signature = classic.get("signature") or federation.get("signature")
    if not public_key or not signature:
        raise HTTPException(status_code=400, detail="Missing classic federation signature")
    return algorithm, public_key, signature


def _extract_pqc(federation: dict[str, Any]) -> tuple[str, str, str] | None:
    signatures = federation.get("signatures") or {}
    pqc = signatures.get("pqc")
    if not pqc:
        return None
    algorithm = pqc.get("algorithm") or PQC_SIG_TARGET
    public_key = pqc.get("public_key")
    signature = pqc.get("signature")
    if not public_key or not signature:
        return None
    return algorithm, public_key, signature


def verify_federation_signatures(
    federation: dict[str, Any],
    message: str,
    *,
    trusted_public_key: str | None = None,
    trusted_pqc_public_key: str | None = None,
) -> None:
    """Verify federation signatures; raises HTTPException on failure."""
    suite_id = federation.get("crypto_suite") or SUITE_V01_CLASSIC
    if not suite_meets_minimum(suite_id):
        raise HTTPException(
            status_code=400,
            detail=f"Crypto suite {suite_id} below node minimum {minimum_accepted_crypto_suite()}",
        )

    _, classic_pub, classic_sig = _extract_classic(federation)
    if trusted_public_key:
        classic_pub = trusted_public_key
    if not verify_message(message, classic_sig, classic_pub):
        raise HTTPException(status_code=400, detail="Invalid classic federation signature")

    spec = suite_spec(suite_id)
    pqc = _extract_pqc(federation)
    need_pqc = spec.get("hybrid") or require_pqc_signature()

    if need_pqc and pqc is None:
        raise HTTPException(status_code=400, detail="PQC signature required for crypto suite")

    if pqc is None:
        return

    algorithm, pqc_pub, pqc_sig = pqc
    if trusted_pqc_public_key:
        pqc_pub = trusted_pqc_public_key

    if not verify_pqc(message, algorithm, pqc_pub, pqc_sig):
        raise HTTPException(status_code=400, detail="Invalid PQC federation signature")


def federation_signatures_valid(
    federation: dict[str, Any],
    message: str,
    *,
    trusted_public_key: str | None = None,
    trusted_pqc_public_key: str | None = None,
) -> bool:
    """Return True when federation signatures verify; False on any failure."""
    try:
        verify_federation_signatures(
            federation,
            message,
            trusted_public_key=trusted_public_key,
            trusted_pqc_public_key=trusted_pqc_public_key,
        )
        return True
    except HTTPException:
        return False


def crypto_readiness_report() -> dict[str, Any]:
    """Node-level quantum readiness snapshot for operators and federation peers."""
    suite = active_crypto_suite()
    spec = suite_spec(suite)
    classic_pub = get_node_public_key_hex()
    pqc_pub = get_pqc_public_key_hex()
    pqc_status = pqc_implementation_status()
    return {
        "quantum_readiness": "transition" if spec.get("hybrid") else "classic",
        "active_crypto_suite": suite,
        "active_hash_algorithm": active_hash_algorithm(),
        "minimum_accepted_crypto_suite": minimum_accepted_crypto_suite(),
        "require_pqc_signature": require_pqc_signature(),
        "hash_algorithm": spec["hash_algorithm"],
        "signature_algorithms": spec["signature_algorithms"],
        "hybrid_signing_enabled": bool(spec.get("hybrid") and classic_pub and pqc_pub),
        "classic_public_key_configured": classic_pub is not None,
        "pqc_public_key_configured": pqc_pub is not None,
        "pqc_implementation": pqc_status,
        "pqc_production_target": PQC_SIG_TARGET,
        "available_suites": list_crypto_suites(),
        "policy": {
            "traceable_finalization_required": True,
            "re_sign_campaign": "High-value proofs should re-sign when upgrading suites",
            "anchor_dual_publish": "Publish merkle_root + graph_merkle_root under hybrid suite",
            "ledger_hash_agility": "New rows use active_hash_algorithm(); legacy sha256 preserved",
        },
        "nist_reference": "ML-DSA (FIPS 204) + SHA-256/SHA-3 hybrid transition",
    }
