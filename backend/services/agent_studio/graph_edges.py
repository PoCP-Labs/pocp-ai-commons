"""Append Meta Agent Studio orchestration edges to the contribution graph."""

from __future__ import annotations

from sqlalchemy.orm import Session

from meta_agents_spec import META_AGENT_BY_ID, META_AGENT_IDS, NEXUS_ID
from models.agent_studio import AgentStudioHandoff
from models.entity import Entity
from services.org_foundation import POCP_ORG_NAME

_STUDIO_RELATIONS = frozenset({"reports_to", "orchestrates", "handoff_to", "maintains"})


def append_meta_agent_studio_graph_edges(
    db: Session,
    *,
    edges: list,
    nodes: list,
    node_ids: set,
    entity_map: dict,
    append_edge,
) -> dict:
    """Add structural + studio-layer edges for Meta Agent orchestration."""
    added = {"reports_to": 0, "orchestrates": 0, "handoff_to": 0, "maintains": 0}

    org = db.query(Entity).filter(Entity.name == POCP_ORG_NAME).first()

    for eid in META_AGENT_IDS:
        entity = entity_map.get(eid)
        if entity is None:
            continue
        meta = entity.metadata_ or {}
        reports_to = meta.get("reports_to")
        if reports_to and reports_to in node_ids:
            append_edge(
                edges,
                {
                    "source": eid,
                    "target": reports_to,
                    "relation": "reports_to",
                    "contribution_id": None,
                    "weight": 1.0,
                    "connection_layer": "studio",
                    "studio": True,
                },
            )
            added["reports_to"] += 1

        spec = META_AGENT_BY_ID.get(eid, {})
        if eid == NEXUS_ID:
            for child_id in spec.get("orchestrates") or []:
                if child_id in node_ids:
                    append_edge(
                        edges,
                        {
                            "source": NEXUS_ID,
                            "target": child_id,
                            "relation": "orchestrates",
                            "contribution_id": None,
                            "weight": 1.0,
                            "connection_layer": "studio",
                            "studio": True,
                        },
                    )
                    added["orchestrates"] += 1

        if org and eid in node_ids and org.id in node_ids:
            append_edge(
                edges,
                {
                    "source": org.id,
                    "target": eid,
                    "relation": "maintains",
                    "contribution_id": None,
                    "weight": 1.0,
                    "connection_layer": "studio",
                    "studio": True,
                },
            )
            added["maintains"] += 1

    handoffs = (
        db.query(AgentStudioHandoff)
        .order_by(AgentStudioHandoff.created_at.desc())
        .limit(200)
        .all()
    )
    for h in handoffs:
        if h.from_agent_entity_id not in node_ids or h.to_agent_entity_id not in node_ids:
            continue
        append_edge(
            edges,
            {
                "source": h.from_agent_entity_id,
                "target": h.to_agent_entity_id,
                "relation": "handoff_to",
                "contribution_id": None,
                "weight": 1.0 if h.status.value == "completed" else 0.5,
                "connection_layer": "studio",
                "studio": True,
                "handoff_id": h.id,
                "mission_id": h.mission_id,
                "handoff_status": h.status.value,
            },
        )
        added["handoff_to"] += 1

    meta_agent_nodes = 0
    for node in nodes:
        if node["id"] in META_AGENT_IDS:
            node["meta_agent"] = True
            node["studio_layer"] = True
            node["layout_column"] = "meta_agent"
            meta_agent_nodes += 1

    return {
        "studio_edge_counts": added,
        "handoff_edges": added["handoff_to"],
        "meta_agent_nodes": meta_agent_nodes,
    }
