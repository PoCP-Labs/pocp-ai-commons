"""Merkle tree for ledger record hashes — Bitcoin SPV-style inclusion proofs."""

from __future__ import annotations

import hashlib
from typing import Any


def _pair_hash(left: str, right: str) -> str:
    return hashlib.sha256(f"{left}{right}".encode("utf-8")).hexdigest()


def merkle_root(hashes: list[str]) -> str:
    if not hashes:
        return hashlib.sha256(b"").hexdigest()
    layer = hashes[:]
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        next_layer = []
        for i in range(0, len(layer), 2):
            next_layer.append(_pair_hash(layer[i], layer[i + 1]))
        layer = next_layer
    return layer[0]


def build_merkle_inclusion_proof(hashes: list[str], index: int) -> list[dict[str, str]]:
    """Return sibling path from leaf at index to root (SPV-style)."""
    if not hashes or index < 0 or index >= len(hashes):
        return []

    layer = hashes[:]
    idx = index
    proof: list[dict[str, str]] = []

    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer = layer + [layer[-1]]
        next_layer: list[str] = []
        for i in range(0, len(layer), 2):
            next_layer.append(_pair_hash(layer[i], layer[i + 1]))
        if idx % 2 == 0:
            proof.append({"position": "right", "hash": layer[idx + 1]})
        else:
            proof.append({"position": "left", "hash": layer[idx - 1]})
        idx //= 2
        layer = next_layer

    return proof


def verify_merkle_inclusion(
    leaf_hash: str,
    proof_steps: list[dict[str, str]],
    expected_root: str,
) -> bool:
    computed = leaf_hash
    for step in proof_steps:
        sibling = step.get("hash")
        if not sibling:
            return False
        if step.get("position") == "right":
            computed = _pair_hash(computed, sibling)
        else:
            computed = _pair_hash(sibling, computed)
    return computed == expected_root


def build_inclusion_bundle(hashes: list[str], target_hash: str) -> dict[str, Any] | None:
    """Build SPV bundle for one record hash within the full ledger Merkle tree."""
    try:
        index = hashes.index(target_hash)
    except ValueError:
        return None

    root = merkle_root(hashes)
    proof_steps = build_merkle_inclusion_proof(hashes, index)
    return {
        "leaf_hash": target_hash,
        "leaf_index": index,
        "tree_size": len(hashes),
        "merkle_root": root,
        "merkle_proof": proof_steps,
        "algorithm": "sha256-pair-concat-v0.1",
        "note": "Anyone with merkle_root can verify this ledger record was included without full chain replay.",
    }
