"""Merkle commitment over Contribution Graph edges — Bitcoin SPV for collaboration structure."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from services.graph import build_contribution_graph
from services.ledger_merkle import build_inclusion_bundle, merkle_root, verify_merkle_inclusion

GRAPH_MERKLE_ALGORITHM = "sha256-canonical-edge-v0.1"


def canonical_edge_key(edge: dict[str, Any]) -> str:
    """Deterministic string for one graph edge (lexicographic sort key for leaves)."""
    weight = edge.get("weight", 0.0)
    try:
        weight_str = f"{float(weight):.6f}"
    except (TypeError, ValueError):
        weight_str = "0.000000"
    return "|".join(
        [
            str(edge.get("source") or ""),
            str(edge.get("target") or ""),
            str(edge.get("relation") or ""),
            str(edge.get("contribution_id") or ""),
            weight_str,
        ]
    )


def edge_leaf_hash(edge: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_edge_key(edge).encode("utf-8")).hexdigest()


def graph_edge_leaf_hashes(edges: list[dict[str, Any]]) -> list[str]:
    return sorted(edge_leaf_hash(edge) for edge in edges)


def build_graph_merkle_root(edges: list[dict[str, Any]]) -> str:
    return merkle_root(graph_edge_leaf_hashes(edges))


def build_graph_merkle_state(edges: list[dict[str, Any]]) -> dict[str, Any]:
    leaves = graph_edge_leaf_hashes(edges)
    return {
        "graph_merkle_root": merkle_root(leaves),
        "graph_edge_count": len(edges),
        "tree_size": len(leaves),
        "algorithm": GRAPH_MERKLE_ALGORITHM,
    }


def build_contribution_graph_inclusion(
    edges: list[dict[str, Any]],
    contribution_id: str,
) -> dict[str, Any] | None:
    """SPV bundles for all edges belonging to one contribution."""
    matching = [edge for edge in edges if edge.get("contribution_id") == contribution_id]
    if not matching:
        return None

    all_hashes = graph_edge_leaf_hashes(edges)
    root = merkle_root(all_hashes)
    proofs: list[dict[str, Any]] = []

    for edge in matching:
        leaf = edge_leaf_hash(edge)
        if leaf not in all_hashes:
            continue
        bundle = build_inclusion_bundle(all_hashes, leaf)
        if not bundle:
            continue
        bundle["edge"] = {
            "source": edge.get("source"),
            "target": edge.get("target"),
            "relation": edge.get("relation"),
            "contribution_id": contribution_id,
            "weight": edge.get("weight"),
        }
        proofs.append(bundle)

    if not proofs:
        return None

    return {
        "merkle_root": root,
        "graph_algorithm": GRAPH_MERKLE_ALGORITHM,
        "contribution_id": contribution_id,
        "edge_count": len(proofs),
        "tree_size": len(all_hashes),
        "proofs": proofs,
        "note": "Each proof shows one collaboration edge is committed in graph_merkle_root.",
    }


def verify_graph_merkle_inclusion(inclusion: dict[str, Any]) -> bool:
    """Verify all edge proofs in a contribution graph inclusion block."""
    expected_root = inclusion.get("merkle_root") or ""
    proofs = inclusion.get("proofs") or []
    if not expected_root or not proofs:
        return False

    for proof in proofs:
        leaf = proof.get("leaf_hash")
        if not leaf:
            return False
        if proof.get("merkle_root") and proof.get("merkle_root") != expected_root:
            return False
        if not verify_merkle_inclusion(
            leaf,
            proof.get("merkle_proof") or [],
            expected_root,
        ):
            return False
    return True


def build_graph_inclusion_from_db(db: Session, contribution_id: str) -> dict[str, Any] | None:
    graph = build_contribution_graph(db)
    return build_contribution_graph_inclusion(graph["edges"], contribution_id)


def build_graph_delta(db: Session, since: datetime | None = None) -> dict[str, Any]:
    """Incremental graph slice for mirror nodes (headers-first style sync)."""
    from models.contribution import ContributionEvent

    graph = build_contribution_graph(db)
    state = build_graph_merkle_state(graph["edges"])

    if since is None:
        return {
            "mode": "snapshot",
            "since": None,
            **state,
            "nodes": graph["nodes"],
            "edges": graph["edges"],
            "entity_count": graph.get("entity_count", 0),
            "contribution_node_count": graph.get("contribution_node_count", 0),
        }

    recent_contribution_ids = {
        row[0]
        for row in db.query(ContributionEvent.id)
        .filter(ContributionEvent.created_at >= since)
        .all()
    }

    delta_node_ids: set[str] = set()
    delta_edges: list[dict[str, Any]] = []
    for edge in graph["edges"]:
        contribution_id = edge.get("contribution_id")
        if contribution_id and contribution_id in recent_contribution_ids:
            delta_edges.append(edge)
            delta_node_ids.add(edge["source"])
            delta_node_ids.add(edge["target"])

    delta_nodes = [node for node in graph["nodes"] if node["id"] in delta_node_ids]

    return {
        "mode": "delta",
        "since": since.isoformat(),
        **state,
        "contribution_ids": sorted(recent_contribution_ids),
        "new_nodes": delta_nodes,
        "new_edges": delta_edges,
        "new_node_count": len(delta_nodes),
        "new_edge_count": len(delta_edges),
    }
