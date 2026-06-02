"""Unified Merkle tree — same algorithm for ledger, graph, and ProtocolEvent batches."""

from __future__ import annotations

from typing import Any

from services.ledger_merkle import (
    build_inclusion_bundle,
    build_merkle_inclusion_proof,
    merkle_root,
    verify_merkle_inclusion,
)

MERKLE_ALGORITHM = "sha256-pair-concat-v0.1"
MERKLE_LEAF_PREFIX = "sha256:"


def normalize_merkle_leaf(leaf_hash: str) -> str:
    """Strip optional sha256: prefix so ledger and overlay leaves share one tree."""
    if leaf_hash.startswith(MERKLE_LEAF_PREFIX):
        return leaf_hash[len(MERKLE_LEAF_PREFIX) :]
    return leaf_hash


def format_merkle_leaf(leaf_hash: str) -> str:
    """Canonical display form for protocol event / overlay leaves."""
    normalized = normalize_merkle_leaf(leaf_hash)
    return f"{MERKLE_LEAF_PREFIX}{normalized}"


def merkle_root_unified(leaf_hashes: list[str]) -> str:
    """Bare hex root — matches ledger_merkle.merkle_root."""
    if not leaf_hashes:
        return merkle_root([])
    return merkle_root([normalize_merkle_leaf(h) for h in leaf_hashes])


def merkle_root_unified_display(leaf_hashes: list[str]) -> str:
    return format_merkle_leaf(merkle_root_unified(leaf_hashes))


def build_inclusion_bundle_unified(
    leaf_hashes: list[str],
    target_hash: str,
) -> dict[str, Any] | None:
    normalized = [normalize_merkle_leaf(h) for h in leaf_hashes]
    target = normalize_merkle_leaf(target_hash)
    bundle = build_inclusion_bundle(normalized, target)
    if bundle is None:
        return None
    bundle["algorithm"] = MERKLE_ALGORITHM
    bundle["leaf_hash_display"] = format_merkle_leaf(bundle["leaf_hash"])
    bundle["merkle_root_display"] = format_merkle_leaf(bundle["merkle_root"])
    return bundle


def verify_merkle_inclusion_unified(
    leaf_hash: str,
    proof_steps: list[dict[str, str]],
    expected_root: str,
) -> bool:
    return verify_merkle_inclusion(
        normalize_merkle_leaf(leaf_hash),
        proof_steps,
        normalize_merkle_leaf(expected_root),
    )
