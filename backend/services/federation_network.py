"""Federation network overview for UI (nodes, mirrors, edges)."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity, EntityStatus
from services.federation_community import (
    _LOCAL_ENTITY_ID,
    _LOCAL_NODE_ID,
    ensure_federation_peer_entities,
    list_federation_peer_entities,
    peer_entity_id,
)
from services.federation_entity_mirror import list_mirrored_entities
from services.trust_config import load_trusted_nodes, trusted_nodes_source


def _mirror_count_by_home(db: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in db.query(Entity).filter(Entity.status == EntityStatus.active).all():
        meta = row.metadata_ or {}
        if "federated_mirror" not in (meta.get("roles") or []):
            continue
        home = meta.get("home_node_id")
        if home:
            counts[home] = counts.get(home, 0) + 1
    return counts


def build_federation_network_overview(db: Session, *, satellite_limit: int = 36) -> dict[str, Any]:
    """
    Single payload for AI Node / network map:
    - nodes: federation instances (local + trusted + import-inferred)
    - satellites: mirrored remote entities (for ring visualization)
    - edges: precomputed lines for mini-map
    """
    ensure_federation_peer_entities(db)
    db.flush()

    mirror_counts = _mirror_count_by_home(db)
    peer_rows = list_federation_peer_entities(db)
    nodes_by_id: dict[str, dict[str, Any]] = {}

    for row in peer_rows:
        eid = row["entity_id"]
        meta = row.get("metadata") or {}
        node_id = meta.get("node_id") or ""
        nodes_by_id[eid] = {
            "id": eid,
            "entity_id": eid,
            "node_id": node_id,
            "name": row.get("name") or node_id,
            "is_local": bool(row.get("is_local")),
            "kind": "local" if row.get("is_local") else "peer",
            "base_url": meta.get("base_url"),
            "trust_weight": meta.get("trust_weight"),
            "mirror_count": mirror_counts.get(node_id, 0) if node_id else 0,
            "metadata": meta,
        }

    # DB discovered peers (registered but not yet in trust config)
    for row in db.query(Entity).filter(Entity.status == EntityStatus.active).all():
        meta = row.metadata_ or {}
        roles = meta.get("roles") or []
        if "discovered_peer" not in roles:
            continue
        eid = row.id
        node_id = meta.get("node_id") or ""
        if eid in nodes_by_id:
            nodes_by_id[eid]["configured"] = bool(nodes_by_id[eid].get("configured"))
            nodes_by_id[eid]["mirror_count"] = max(
                int(nodes_by_id[eid].get("mirror_count") or 0),
                int(mirror_counts.get(node_id, 0)),
            )
            nodes_by_id[eid]["metadata"] = {**(nodes_by_id[eid].get("metadata") or {}), **meta}
            continue
        nodes_by_id[eid] = {
            "id": eid,
            "entity_id": eid,
            "node_id": node_id,
            "name": row.name or f"Federation Peer · {node_id or 'unknown'}",
            "is_local": False,
            "kind": "peer",
            "base_url": meta.get("base_url"),
            "trust_weight": meta.get("trust_weight"),
            "mirror_count": mirror_counts.get(node_id, 0) if node_id else 0,
            "configured": False,
            "discovered": True,
            "metadata": meta,
        }

    # Trust-configured peers that may not yet have DB rows
    for peer in load_trusted_nodes():
        eid = peer_entity_id(peer.node_id)
        if eid in nodes_by_id:
            nodes_by_id[eid]["trust_weight"] = peer.trust_weight
            nodes_by_id[eid]["base_url"] = peer.base_url.rstrip("/")
            nodes_by_id[eid]["configured"] = True
            continue
        nodes_by_id[eid] = {
            "id": eid,
            "entity_id": eid,
            "node_id": peer.node_id,
            "name": f"Federation Peer · {peer.node_id}",
            "is_local": False,
            "kind": "peer",
            "base_url": peer.base_url.rstrip("/"),
            "trust_weight": peer.trust_weight,
            "mirror_count": mirror_counts.get(peer.node_id, 0),
            "configured": True,
            "metadata": {
                "roles": ["federation_peer", "community"],
                "node_id": peer.node_id,
                "base_url": peer.base_url.rstrip("/"),
            },
        }

    # Peer shells implied by mirrors (home_node_id) even if not in trust list
    for home, count in mirror_counts.items():
        if not home:
            continue
        eid = peer_entity_id(home)
        if eid in nodes_by_id:
            nodes_by_id[eid]["mirror_count"] = count
            continue
        nodes_by_id[eid] = {
            "id": eid,
            "entity_id": eid,
            "node_id": home,
            "name": f"Federation Source · {home}",
            "is_local": False,
            "kind": "peer",
            "base_url": None,
            "trust_weight": None,
            "mirror_count": count,
            "configured": False,
            "inferred_from_mirrors": True,
            "metadata": {"roles": ["federation_peer"], "node_id": home},
        }

    nodes = list(nodes_by_id.values())
    nodes.sort(key=lambda n: (0 if n.get("is_local") else 1, n.get("name") or ""))

    mirrors = list_mirrored_entities(db, limit=satellite_limit)
    satellites = [
        {
            "id": m["entity_id"],
            "entity_id": m["entity_id"],
            "name": m.get("name") or "mirror",
            "entity_type": m.get("entity_type"),
            "home_node_id": m.get("home_node_id"),
            "peer_entity_id": peer_entity_id(m["home_node_id"]) if m.get("home_node_id") else None,
            "kind": "mirror",
        }
        for m in mirrors
    ]

    edges: list[dict[str, Any]] = []
    local_id = _LOCAL_ENTITY_ID
    peer_nodes = [n for n in nodes if not n.get("is_local")]

    for peer in peer_nodes:
        pid = peer["id"]
        if local_id in nodes_by_id and pid:
            edges.append(
                {
                    "source": local_id,
                    "target": pid,
                    "relation": "federated_with",
                }
            )
        for sat in satellites:
            if sat.get("peer_entity_id") == pid:
                edges.append(
                    {
                        "source": pid,
                        "target": sat["id"],
                        "relation": "mirrors_remote",
                    }
                )

    # Local-only mirrors: attach directly to local node for visualization
    if not peer_nodes:
        for sat in satellites:
            edges.append(
                {
                    "source": local_id,
                    "target": sat["id"],
                    "relation": "mirrors_remote",
                }
            )

    trusted = load_trusted_nodes()
    return {
        "schema": "pocp.federation_network_overview.v0.1",
        "local_node_id": os.getenv("POCP_NODE_ID", _LOCAL_NODE_ID),
        "local_entity_id": local_id,
        "trust_source": trusted_nodes_source(),
        "trusted_peer_count": len(trusted),
        "node_count": len(nodes),
        "mirror_count": len(satellites),
        "satellite_limit": satellite_limit,
        "nodes": nodes,
        "satellites": satellites,
        "edges": edges,
        "setup_hint": (
            None
            if trusted
            else {
                "message": "Configure POCP_TRUSTED_NODES or backend/config/trusted_nodes.yaml",
                "example_env": '[{"node_id":"peer-a","base_url":"http://localhost:8009","trust_weight":0.8}]',
            }
        ),
    }
