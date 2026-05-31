"""Structural graph analytics — advisory review priority & centrality (NN-4 lite)."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session, joinedload

from models.contribution import ContributionEvent, ContributionStatus
from services.graph import build_contribution_graph
from services.graph_gnn_advisory import build_gnn_advisory


def _degree_centrality(edges: list[dict]) -> dict[str, float]:
    degree: dict[str, int] = defaultdict(int)
    for edge in edges:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1
    if not degree:
        return {}
    max_deg = max(degree.values()) or 1
    return {node_id: round(count / max_deg, 4) for node_id, count in degree.items()}


def build_graph_analytics(db: Session, *, review_limit: int = 20) -> dict:
    """Advisory graph metrics without PyG — ranks pending review queue by graph signals."""
    graph = build_contribution_graph(db)
    centrality = _degree_centrality(graph["edges"])

    pending = (
        db.query(ContributionEvent)
        .options(
            joinedload(ContributionEvent.participants),
            joinedload(ContributionEvent.ai_verifications),
        )
        .filter(
            ContributionEvent.status.in_(
                [ContributionStatus.submitted, ContributionStatus.ai_verified]
            )
        )
        .all()
    )

    review_hints: list[dict] = []
    for contrib in pending:
        hub_id = f"contribution:{contrib.id}"
        hub_c = centrality.get(hub_id, 0.0)
        participant_c = max(
            (centrality.get(p.entity_id, 0.0) for p in contrib.participants),
            default=0.0,
        )
        witness_count = len(contrib.ai_verifications)
        avg_score = 0.0
        if contrib.ai_verifications:
            avg_score = sum(v.score or 0 for v in contrib.ai_verifications) / len(
                contrib.ai_verifications
            )
        priority = round(0.35 * hub_c + 0.25 * participant_c + 0.25 * avg_score + 0.15 * min(1.0, witness_count / 3), 4)
        review_hints.append(
            {
                "contribution_id": contrib.id,
                "status": contrib.status.value,
                "priority_score": priority,
                "hub_centrality": hub_c,
                "max_participant_centrality": participant_c,
                "witness_count": witness_count,
                "avg_witness_score": round(avg_score, 4),
                "advisory": "review_priority_hint",
            }
        )

    gnn = build_gnn_advisory(graph)
    gnn_by_contrib = {
        h["contribution_id"]: h for h in gnn.get("contribution_gnn_hints") or []
    }
    for hint in review_hints:
        extra = gnn_by_contrib.get(hint["contribution_id"])
        if extra:
            hint["gnn_boost"] = extra.get("max_participant_pagerank")
            hint["priority_score"] = round(
                hint["priority_score"] * 0.7 + extra.get("max_participant_pagerank", 0) * 0.3,
                4,
            )
    review_hints.sort(key=lambda h: h["priority_score"], reverse=True)

    entity_nodes = [n for n in graph["nodes"] if n["entity_type"] not in ("contribution", "ledger", "federation_import")]
    federation_imports = [n for n in graph["nodes"] if n["entity_type"] == "federation_import"]
    top_entities = sorted(
        entity_nodes,
        key=lambda n: centrality.get(n["id"], 0.0),
        reverse=True,
    )[:10]

    return {
        "advisory_only": True,
        "graph_stats": {
            "node_count": len(graph["nodes"]),
            "edge_count": len(graph["edges"]),
            "entity_count": graph.get("entity_count", 0),
            "contribution_node_count": graph.get("contribution_node_count", 0),
            "federation_import_node_count": graph.get("federation_import_node_count", 0),
            "pending_review_count": len(pending),
        },
        "federation_signals": {
            "imported_contribution_nodes": len(federation_imports),
            "note": "Higher import count suggests cross-node memory sync is active.",
        },
        "high_centrality_entities": [
            {
                "entity_id": n["id"],
                "name": n["name"],
                "entity_type": n["entity_type"],
                "centrality": centrality.get(n["id"], 0.0),
                "reputation": n.get("reputation", 0),
            }
            for n in top_entities
        ],
        "review_queue_hints": review_hints[:review_limit],
        "gnn_advisory": gnn,
        "sourcecred_advisory": {
            "inspiration": "github:sourcecred/sourcecred",
            "status": "evaluating",
            "credrank_method": gnn.get("method", "pagerank_v0.1"),
            "top_entity_pagerank": (gnn.get("top_entity_pagerank") or [])[:5],
            "plugin_model": "PoCP contribution graph as instance-specific plugin surface",
            "notes": "PageRank propagation inspired by SourceCred CredRank; advisory only — no Grain/token.",
            "mapping_doc": "docs/inspiration-mappings/sourcecred.md",
        },
        "method": gnn.get("method", "structural_centrality_v0.1"),
        "notes": "Combines degree-centrality queue ranking with PageRank/GNN propagation hints.",
    }
