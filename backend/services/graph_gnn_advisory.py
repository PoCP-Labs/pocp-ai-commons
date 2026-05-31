"""Graph neural advisory — PageRank propagation + optional PyG GCN (NN-4)."""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any


def pyg_gnn_enabled() -> bool:
    return os.getenv("ENABLE_PYG_GRAPH_ADVISORY", "false").lower() in ("true", "1", "yes", "on")


def pyg_available() -> bool:
    if not pyg_gnn_enabled():
        return False
    try:
        import torch  # noqa: F401
        from torch_geometric.nn import GCNConv  # noqa: F401

        return True
    except Exception:
        return False


def _build_adjacency(edges: list[dict]) -> tuple[dict[str, list[str]], list[str]]:
    adj: dict[str, list[str]] = defaultdict(list)
    nodes: set[str] = set()
    for edge in edges:
        src, tgt = edge["source"], edge["target"]
        nodes.add(src)
        nodes.add(tgt)
        adj[src].append(tgt)
        adj[tgt].append(src)
    return adj, sorted(nodes)


def pagerank_scores(edges: list[dict], *, iterations: int = 25, damping: float = 0.85) -> dict[str, float]:
    """Lightweight PageRank — GNN-free baseline for entity importance."""
    adj, node_ids = _build_adjacency(edges)
    if not node_ids:
        return {}
    n = len(node_ids)
    idx = {node_id: i for i, node_id in enumerate(node_ids)}
    rank = [1.0 / n] * n
    out_degree = [max(len(adj[node_id]), 1) for node_id in node_ids]

    for _ in range(iterations):
        new_rank = [(1.0 - damping) / n] * n
        for target_i, target_id in enumerate(node_ids):
            for source_id in adj[target_id]:
                source_i = idx[source_id]
                new_rank[target_i] += damping * rank[source_i] / out_degree[source_i]
        rank = new_rank

    max_rank = max(rank) or 1.0
    return {node_ids[i]: round(rank[i] / max_rank, 4) for i in range(n)}


def _pyg_node_embeddings(edges: list[dict], node_ids: list[str]) -> dict[str, float] | None:
    """Optional 1-layer GCN scalar embedding per node (requires torch + PyG)."""
    if not pyg_available() or len(node_ids) < 3:
        return None
    try:
        import torch
        from torch_geometric.data import Data
        from torch_geometric.nn import GCNConv

        idx = {node_id: i for i, node_id in enumerate(node_ids)}
        edge_index = []
        for edge in edges:
            s, t = edge["source"], edge["target"]
            if s in idx and t in idx:
                edge_index.append([idx[s], idx[t]])
                edge_index.append([idx[t], idx[s]])
        if not edge_index:
            return None

        x = torch.ones(len(node_ids), 1)
        ei = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
        data = Data(x=x, edge_index=ei)
        conv = GCNConv(1, 1)
        with torch.no_grad():
            out = conv(data.x, data.edge_index).squeeze()
        values = out.tolist()
        if isinstance(values, float):
            values = [values]
        max_v = max(abs(v) for v in values) or 1.0
        return {node_ids[i]: round(float(values[i]) / max_v, 4) for i in range(len(node_ids))}
    except Exception:
        return None


def build_gnn_advisory(graph: dict[str, Any]) -> dict[str, Any]:
    """Advisory entity / contribution importance from graph propagation."""
    edges = graph.get("edges") or []
    nodes = graph.get("nodes") or []
    pr = pagerank_scores(edges)
    entity_ids = {
        n["id"]
        for n in nodes
        if n.get("entity_type") not in ("contribution", "ledger", "federation_import")
    }
    gnn = _pyg_node_embeddings(edges, sorted(entity_ids)) if entity_ids else None

    top_pagerank = sorted(
        (
            {
                "entity_id": nid,
                "name": next((n["name"] for n in nodes if n["id"] == nid), nid),
                "entity_type": next((n["entity_type"] for n in nodes if n["id"] == nid), "unknown"),
                "pagerank": score,
                "gnn_score": (gnn or {}).get(nid),
            }
            for nid, score in pr.items()
            if nid in entity_ids
        ),
        key=lambda x: x["pagerank"],
        reverse=True,
    )[:15]

    contribution_scores: list[dict] = []
    for node in nodes:
        if node.get("entity_type") != "contribution":
            continue
        hub_id = node["id"]
        contrib_id = hub_id.split(":", 1)[-1] if ":" in hub_id else hub_id
        participant_pr = [
            pr.get(edge["source"], 0.0)
            for edge in edges
            if edge.get("target") == hub_id and edge.get("source") in entity_ids
        ]
        boost = max(participant_pr, default=0.0)
        contribution_scores.append(
            {
                "contribution_id": contrib_id,
                "hub_pagerank": pr.get(hub_id, 0.0),
                "max_participant_pagerank": round(boost, 4),
                "gnn_boost": round(max((gnn or {}).get(e["source"], 0.0) for e in edges if e.get("target") == hub_id), 4)
                if gnn
                else None,
                "advisory": "gnn_review_priority",
            }
        )
    contribution_scores.sort(
        key=lambda x: (x["max_participant_pagerank"], x["hub_pagerank"]),
        reverse=True,
    )

    return {
        "advisory_only": True,
        "method": "pyg_gcn_v0.1" if gnn else "pagerank_v0.1",
        "pyg_available": pyg_available(),
        "top_entity_pagerank": top_pagerank,
        "contribution_gnn_hints": contribution_scores[:20],
    }
