"""Federation peer nodes as community entities on the contribution graph."""

from __future__ import annotations

import os
import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity, EntityStatus, EntityType
from models.federation import FederatedImport
from schemas.federation import TrustedNode
from services.org_foundation import POCP_ORG_NAME
from services.trust_config import load_trusted_nodes

_LOCAL_NODE_ID = os.getenv("POCP_NODE_ID", f"pocp-node-{uuid.uuid4().hex[:8]}")
_LOCAL_ENTITY_ID = "pocp-entity-federation-local"
_PEER_ID_PREFIX = "pocp-entity-federation-peer-"
_FEDERATION_IMPORT_PREFIX = "federation-import:"


def _sanitize_node_id(node_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "-", node_id.strip().lower())
    return cleaned[:48] or "unknown"


def peer_entity_id(node_id: str) -> str:
    return f"{_PEER_ID_PREFIX}{_sanitize_node_id(node_id)}"


def local_federation_entity_id() -> str:
    return _LOCAL_ENTITY_ID


def _pocp_org_entity(db: Session) -> Entity | None:
    return db.query(Entity).filter(Entity.name == POCP_ORG_NAME).first()


def _peer_entity_spec(peer: TrustedNode) -> dict[str, Any]:
    entity_id = peer_entity_id(peer.node_id)
    portable_id = f"pocp:federation:{peer.node_id}"
    return {
        "id": entity_id,
        "entity_type": EntityType.community,
        "name": f"Federation Peer · {peer.node_id}",
        "description": f"Trusted federated PoCP node at {peer.base_url.rstrip('/')}",
        "metadata_": {
            "roles": ["federation_peer", "community"],
            "node_id": peer.node_id,
            "base_url": peer.base_url.rstrip("/"),
            "public_key": peer.public_key,
            "trust_weight": peer.trust_weight,
            "portable_id": portable_id,
            "registry": "trusted_nodes",
        },
    }


def federation_import_hub_id(import_id: str) -> str:
    return f"{_FEDERATION_IMPORT_PREFIX}{import_id}"


def _import_source_entity_spec(node_id: str) -> dict[str, Any]:
    trusted = {p.node_id: p for p in load_trusted_nodes()}
    peer = trusted.get(node_id)
    if peer:
        return _peer_entity_spec(peer)
    entity_id = peer_entity_id(node_id)
    return {
        "id": entity_id,
        "entity_type": EntityType.community,
        "name": f"Federation Source · {node_id}",
        "description": f"Federated contribution source node {node_id}",
        "metadata_": {
            "roles": ["federation_peer", "community"],
            "node_id": node_id,
            "portable_id": f"pocp:federation:{node_id}",
            "registry": "federated_imports",
            "inferred_from_imports": True,
        },
    }


def ensure_import_source_peer_entities(db: Session) -> list[Entity]:
    """Ensure community entities exist for every federation import source node."""
    source_ids = {
        row[0]
        for row in db.query(FederatedImport.source_node_id).distinct().all()
        if row[0]
    }
    created: list[Entity] = []
    org = _pocp_org_entity(db)
    for node_id in sorted(source_ids):
        spec = _import_source_entity_spec(node_id)
        entity = db.get(Entity, spec["id"])
        if entity is None:
            entity = Entity(
                id=spec["id"],
                entity_type=spec["entity_type"],
                name=spec["name"],
                description=spec["description"][:500],
                status=EntityStatus.active,
                metadata_=spec["metadata_"],
            )
            db.add(entity)
            created.append(entity)
        elif spec["metadata_"].get("inferred_from_imports"):
            entity.metadata_ = {**(entity.metadata_ or {}), **spec["metadata_"]}
        if org is not None:
            entity.creator_id = org.id
    db.flush()
    return created


def ensure_federation_peer_entities(db: Session) -> list[Entity]:
    """Create or refresh community Entity rows for trusted federation peers and local node."""
    created = ensure_import_source_peer_entities(db)
    org = _pocp_org_entity(db)
    peers = load_trusted_nodes()

    local_backend = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    local_spec = {
        "id": _LOCAL_ENTITY_ID,
        "entity_type": EntityType.community,
        "name": f"Local Node · {_LOCAL_NODE_ID}",
        "description": f"This PoCP federation node ({local_backend})",
        "metadata_": {
            "roles": ["federation_node", "community"],
            "node_id": _LOCAL_NODE_ID,
            "base_url": local_backend,
            "portable_id": f"pocp:federation:{_LOCAL_NODE_ID}",
            "node_mode": os.getenv("POCP_NODE_MODE", "full"),
            "registry": "local_node",
        },
    }

    specs = [local_spec] + [_peer_entity_spec(peer) for peer in peers]

    for spec in specs:
        entity = db.get(Entity, spec["id"])
        if entity is None:
            entity = Entity(
                id=spec["id"],
                entity_type=spec["entity_type"],
                name=spec["name"],
                description=spec["description"][:500],
                status=EntityStatus.active,
                metadata_=spec["metadata_"],
            )
            db.add(entity)
            created.append(entity)
        else:
            entity.name = spec["name"]
            entity.description = spec["description"][:500]
            entity.entity_type = EntityType.community
            entity.metadata_ = {**(entity.metadata_ or {}), **spec["metadata_"]}
        if org is not None:
            entity.creator_id = org.id

    db.flush()
    return created


def _serialize_import(record: FederatedImport, entity_map: dict[str, Entity] | None = None) -> dict[str, Any]:
    entity_map = entity_map or {}
    primary = entity_map.get(record.primary_entity_id)
    peer_id = peer_entity_id(record.source_node_id)
    peer = entity_map.get(peer_id)
    return {
        "id": record.id,
        "source_node_id": record.source_node_id,
        "source_contribution_id": record.source_contribution_id,
        "peer_entity_id": peer_id,
        "peer_entity_name": peer.name if peer else None,
        "primary_entity_id": record.primary_entity_id,
        "primary_entity_name": primary.name if primary else None,
        "primary_portable_id": record.primary_portable_id,
        "task_title": record.task_title,
        "contribution_type": record.contribution_type,
        "trust_weight": record.trust_weight,
        "reputation_applied": record.reputation_applied,
        "imported_at": record.imported_at.isoformat(),
        "graph_hub_id": federation_import_hub_id(record.id),
    }


def list_entity_federation_imports(db: Session, entity_id: str, *, limit: int = 50) -> dict[str, Any]:
    """Imports where entity is primary contributor or federation peer."""
    ensure_federation_peer_entities(db)
    entities = db.query(Entity).all()
    entity_map = {e.id: e for e in entities}
    entity = entity_map.get(entity_id)
    peer_node_id = (entity.metadata_ or {}).get("node_id") if entity else None

    as_primary = (
        db.query(FederatedImport)
        .filter(FederatedImport.primary_entity_id == entity_id)
        .order_by(FederatedImport.imported_at.desc())
        .limit(limit)
        .all()
    )
    as_peer: list[FederatedImport] = []
    if peer_node_id:
        as_peer = (
            db.query(FederatedImport)
            .filter(FederatedImport.source_node_id == peer_node_id)
            .order_by(FederatedImport.imported_at.desc())
            .limit(limit)
            .all()
        )

    return {
        "entity_id": entity_id,
        "received_imports": [_serialize_import(r, entity_map) for r in as_primary],
        "exported_imports": [_serialize_import(r, entity_map) for r in as_peer],
        "received_count": len(as_primary),
        "exported_count": len(as_peer),
    }


def list_peer_node_imports(db: Session, node_id: str, *, limit: int = 50) -> dict[str, Any]:
    ensure_federation_peer_entities(db)
    entity_map = {e.id: e for e in db.query(Entity).all()}
    rows = (
        db.query(FederatedImport)
        .filter(FederatedImport.source_node_id == node_id)
        .order_by(FederatedImport.imported_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "node_id": node_id,
        "peer_entity_id": peer_entity_id(node_id),
        "import_count": len(rows),
        "imports": [_serialize_import(r, entity_map) for r in rows],
    }


def federation_import_graph_summary(db: Session) -> dict[str, Any]:
    rows = db.query(FederatedImport).order_by(FederatedImport.imported_at.desc()).limit(100).all()
    entity_map = {e.id: e for e in db.query(Entity).all()}
    return {
        "import_count": db.query(FederatedImport).count(),
        "recent": [_serialize_import(r, entity_map) for r in rows[:20]],
    }


def list_federation_peer_entities(db: Session) -> list[dict[str, Any]]:
    """Return community entity snapshots for local node and configured peers."""
    ensure_federation_peer_entities(db)
    entity_ids = [_LOCAL_ENTITY_ID] + [peer_entity_id(p.node_id) for p in load_trusted_nodes()]
    import_source_ids = {
        peer_entity_id(row[0])
        for row in db.query(FederatedImport.source_node_id).distinct().all()
        if row[0]
    }
    entity_ids = list(dict.fromkeys(entity_ids + list(import_source_ids)))
    rows = db.query(Entity).filter(Entity.id.in_(entity_ids)).all() if entity_ids else []
    by_id = {row.id: row for row in rows}
    ordered = [by_id[eid] for eid in entity_ids if eid in by_id]
    return [
        {
            "entity_id": e.id,
            "name": e.name,
            "description": e.description,
            "entity_type": e.entity_type.value,
            "metadata": e.metadata_ or {},
            "is_local": e.id == _LOCAL_ENTITY_ID,
        }
        for e in ordered
    ]


def append_federation_peer_graph_edges(
    db: Session,
    *,
    edges: list[dict],
    entity_map: dict[str, Entity],
    append_edge,
) -> None:
    """Link org and local node to federation peer community entities."""
    org = _pocp_org_entity(db)
    local_id = _LOCAL_ENTITY_ID
    if local_id in entity_map and org is not None:
        append_edge(
            edges,
            {
                "source": org.id,
                "target": local_id,
                "relation": "hosts",
                "contribution_id": None,
                "weight": 1.0,
            },
        )

    peer_ids_seen: set[str] = set()
    for peer in load_trusted_nodes():
        peer_id = peer_entity_id(peer.node_id)
        peer_ids_seen.add(peer_id)
        if peer_id not in entity_map:
            continue
        if org is not None:
            append_edge(
                edges,
                {
                    "source": org.id,
                    "target": peer_id,
                    "relation": "trusts_peer",
                    "contribution_id": None,
                    "weight": float(peer.trust_weight),
                },
            )
        if local_id in entity_map:
            append_edge(
                edges,
                {
                    "source": local_id,
                    "target": peer_id,
                    "relation": "federated_with",
                    "contribution_id": None,
                    "weight": float(peer.trust_weight),
                },
            )

    for row in db.query(FederatedImport.source_node_id).distinct().all():
        node_id = row[0]
        if not node_id:
            continue
        peer_id = peer_entity_id(node_id)
        if peer_id in peer_ids_seen or peer_id not in entity_map or org is None:
            continue
        append_edge(
            edges,
            {
                "source": org.id,
                "target": peer_id,
                "relation": "trusts_peer",
                "contribution_id": None,
                "weight": 0.5,
            },
        )


def append_federated_import_graph_edges(
    db: Session,
    *,
    nodes: list[dict],
    node_ids: set[str],
    edges: list[dict],
    entity_map: dict[str, Entity],
    append_edge,
) -> None:
    """Add federation import hub nodes and cross-node contribution edges."""
    ensure_federation_peer_entities(db)
    local_id = _LOCAL_ENTITY_ID
    imports = db.query(FederatedImport).order_by(FederatedImport.imported_at.desc()).all()

    for record in imports:
        hub_id = federation_import_hub_id(record.id)
        label = record.task_title.strip() if record.task_title else "Federated import"
        if len(label) > 36:
            label = f"{label[:35]}…"

        if hub_id not in node_ids:
            nodes.append(
                {
                    "id": hub_id,
                    "entity_type": "federation_import",
                    "name": label,
                    "reputation": round(record.reputation_applied, 2),
                    "cp_balance": 0,
                    "ai_credits": 0,
                }
            )
            node_ids.add(hub_id)

        peer_id = peer_entity_id(record.source_node_id)
        if peer_id in entity_map:
            append_edge(
                edges,
                {
                    "source": peer_id,
                    "target": hub_id,
                    "relation": "exported_contribution",
                    "contribution_id": None,
                    "weight": float(record.trust_weight),
                },
            )

        if record.primary_entity_id in entity_map:
            append_edge(
                edges,
                {
                    "source": hub_id,
                    "target": record.primary_entity_id,
                    "relation": "imported_to",
                    "contribution_id": None,
                    "weight": float(record.reputation_applied or 1.0),
                },
            )

        if local_id in entity_map:
            append_edge(
                edges,
                {
                    "source": local_id,
                    "target": hub_id,
                    "relation": "received_import",
                    "contribution_id": None,
                    "weight": float(record.trust_weight),
                },
            )


def build_federation_import_context(
    db: Session | None,
    *,
    contribution_id: str,
    primary_entity_id: str,
) -> dict[str, Any]:
    """Proof-layer context linking contribution to federated import graph."""
    if db is None:
        return {
            "spec_version": "pocp.federation_import_context.v0.1",
            "contribution_id": contribution_id,
            "primary_entity_id": primary_entity_id,
            "import_count_for_primary": 0,
            "recent_imports": [],
            "peer_entity_count": 0,
            "local_node_entity_id": local_federation_entity_id(),
            "graph_relations": ["exported_contribution", "imported_to", "received_import", "trusts_peer"],
            "note": "Cross-node reputation imports recorded as community graph hubs.",
        }

    ensure_federation_peer_entities(db)
    entity_map = {e.id: e for e in db.query(Entity).all()}

    received = (
        db.query(FederatedImport)
        .filter(FederatedImport.primary_entity_id == primary_entity_id)
        .order_by(FederatedImport.imported_at.desc())
        .limit(10)
        .all()
    )
    serialized = [_serialize_import(r, entity_map) for r in received]
    peer_entities = list_federation_peer_entities(db)

    return {
        "spec_version": "pocp.federation_import_context.v0.1",
        "contribution_id": contribution_id,
        "primary_entity_id": primary_entity_id,
        "import_count_for_primary": len(received),
        "recent_imports": serialized,
        "peer_entity_count": len([p for p in peer_entities if not p.get("is_local")]),
        "local_node_entity_id": local_federation_entity_id(),
        "graph_relations": ["exported_contribution", "imported_to", "received_import", "trusts_peer"],
        "note": "Cross-node reputation imports recorded as community graph hubs.",
    }


def get_contribution_federation_context(
    db: Session,
    contribution: Any,
) -> dict[str, Any]:
    ctx = build_federation_import_context(
        db,
        contribution_id=contribution.id,
        primary_entity_id=contribution.primary_entity_id,
    )
    ctx["compat"] = "pocp.federation_import_context.v0.1"
    return ctx
