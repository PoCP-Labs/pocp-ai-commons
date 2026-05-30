"""Merkle attribution proofs for code builder impact (contributor-attribution inspired)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from services.code_attribution_bridge import build_code_attribution_context


def _hash_leaf(material: str) -> str:
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _merkle_root(leaves: list[str]) -> str:
    if not leaves:
        return _hash_leaf("")
    layer = [_hash_leaf(leaf) for leaf in leaves]
    while len(layer) > 1:
        next_layer: list[str] = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else left
            next_layer.append(_hash_leaf(left + right))
        layer = next_layer
    return layer[0]


def _merkle_proof(leaves: list[str], index: int) -> list[dict[str, str]]:
    if not leaves:
        return []
    layer = [_hash_leaf(leaf) for leaf in leaves]
    indices = list(range(len(leaves)))
    proof: list[dict[str, str]] = []
    idx = index

    while len(layer) > 1:
        next_layer: list[str] = []
        next_indices: list[int] = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else left
            next_layer.append(_hash_leaf(left + right))
            next_indices.append(i // 2)
            if i == idx or i + 1 == idx:
                sibling = right if i == idx else left
                proof.append(
                    {
                        "position": "right" if i == idx else "left",
                        "hash": sibling,
                    }
                )
                idx = i // 2
        layer = next_layer
        indices = next_indices
    return proof


def build_attribution_merkle_proof(evidence: dict | None) -> dict[str, Any]:
    context = build_code_attribution_context(evidence)
    builders = context.get("builders_involved") or []
    entries: list[dict[str, Any]] = []

    for builder in builders:
        paths = sorted(set(builder.get("matched_paths") or []))
        share = round(max(len(paths), 1) / max(sum(len(b.get("matched_paths") or []) for b in builders), 1), 4)
        entries.append(
            {
                "slug": builder.get("slug"),
                "display_name": builder.get("display_name"),
                "entity_id": builder.get("entity_id"),
                "matched_paths": paths,
                "share": share,
            }
        )

    leaves = [
        json.dumps(
            {
                "slug": entry["slug"],
                "entity_id": entry["entity_id"],
                "paths": entry["matched_paths"],
                "share": entry["share"],
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        for entry in sorted(entries, key=lambda item: item["slug"] or "")
    ]
    root = _merkle_root(leaves)
    proofs = []
    for idx, entry in enumerate(sorted(entries, key=lambda item: item["slug"] or "")):
        proofs.append(
            {
                **entry,
                "leaf_index": idx,
                "leaf_hash": _hash_leaf(leaves[idx]) if leaves else None,
                "merkle_proof": _merkle_proof(leaves, idx),
            }
        )

    return {
        "merkle_root": root,
        "leaf_count": len(leaves),
        "builders": proofs,
        "path_hints": context.get("path_hints") or [],
        "compat": "contributor-attribution-merkle-v0",
        "note": "Anyone with the root can verify a builder share without trusting the analysis server.",
    }


def verify_attribution_merkle_proof(proof: dict[str, Any], builder_slug: str) -> bool:
    builders = proof.get("builders") or []
    target = next((item for item in builders if item.get("slug") == builder_slug), None)
    if not target or not target.get("leaf_hash"):
        return False

    computed = target["leaf_hash"]
    for step in target.get("merkle_proof") or []:
        sibling = step.get("hash")
        if not sibling:
            return False
        if step.get("position") == "right":
            computed = _hash_leaf(computed + sibling)
        else:
            computed = _hash_leaf(sibling + computed)
    return computed == proof.get("merkle_root")
