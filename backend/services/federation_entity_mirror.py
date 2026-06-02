"""Mirror remote PoCP node entities onto the local contribution graph."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity, EntityStatus, EntityType
from services.federation_community import ensure_federation_peer_entities, peer_entity_id
from services.federation_peers import _get_json, probe_peer
from services.trust_config import load_trusted_nodes, trusted_nodes_map

logger = logging.getLogger(__name__)

REMOTE_MIRROR_NS = uuid.UUID("a3f2c8e1-9b4d-4e6f-8a1c-2d5e7f9b0c3d")


def remote_mirror_entity_id(node_id: str, remote_entity_id: str) -> str:
    """Stable local id for an entity that lives on another node."""
    return str(uuid.uuid5(REMOTE_MIRROR_NS, f"{node_id}:{remote_entity_id}"))


def portable_id_for_remote(node_id: str, remote: dict[str, Any]) -> str:
    meta = remote.get("metadata") or {}
    if meta.get("portable_id"):
        return str(meta["portable_id"])
    et = remote.get("entity_type") or "entity"
    name = (remote.get("name") or remote.get("id") or "unknown").replace(" ", "-")[:40]
    return f"pocp:{node_id}:{et}:{name}"


def fetch_peer_entity_catalog(
    base_url: str,
    *,
    entity_type: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Pull public entity list from a trusted peer (GET /api/v1/entities)."""
    root = base_url.rstrip("/")
    qs = f"?entity_type={entity_type}" if entity_type else ""
    data = _get_json(f"{root}/api/v1/entities{qs}")
    items: list[dict[str, Any]]
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and isinstance(data.get("items"), list):
        items = data["items"]
    else:
        items = []
    return items[:limit] if limit else items


def mirror_peer_entities(
    db: Session,
    node_id: str,
    *,
    entity_types: list[str] | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """
    Register trusted peer node entities locally as mirrored shadows.
    - Federation peer → community Entity (node shell)
    - Remote skills/agents/... → local Entity rows with home_node_id metadata
    """
    peer = trusted_nodes_map().get(node_id)
    if peer is None:
        raise ValueError(f"node_id {node_id} not in POCP_TRUSTED_NODES")

    ensure_federation_peer_entities(db)

    types = entity_types or ["skill", "agent", "llm", "workflow", "tool"]
    created = 0
    updated = 0
    skipped = 0
    mirrored: list[dict[str, Any]] = []

    for et in types:
        try:
            catalog = fetch_peer_entity_catalog(peer.base_url, entity_type=et, limit=limit)
        except Exception as exc:
            logger.warning("mirror fetch %s type=%s failed: %s", node_id, et, exc)
            continue

        for remote in catalog:
            remote_id = remote.get("id")
            if not remote_id:
                skipped += 1
                continue
            if remote_id.startswith("pocp-entity-federation-"):
                skipped += 1
                continue

            local_id = remote_mirror_entity_id(node_id, remote_id)
            portable = portable_id_for_remote(node_id, remote)
            meta = {
                "roles": ["remote_entity", "federated_mirror"],
                "home_node_id": node_id,
                "remote_entity_id": remote_id,
                "portable_id": portable,
                "peer_base_url": peer.base_url.rstrip("/"),
                "peer_entity_id": peer_entity_id(node_id),
                "mirror_synced_at": datetime.now(timezone.utc).isoformat(),
            }

            try:
                entity_type = EntityType(remote.get("entity_type") or et)
            except ValueError:
                skipped += 1
                continue

            row = db.get(Entity, local_id)
            if row is None:
                row = Entity(
                    id=local_id,
                    entity_type=entity_type,
                    name=f"{remote.get('name', remote_id)} @{node_id}",
                    description=(remote.get("description") or "")[:500] or None,
                    status=EntityStatus.active,
                    metadata_=meta,
                )
                db.add(row)
                created += 1
            else:
                row.name = f"{remote.get('name', remote_id)} @{node_id}"
                row.description = (remote.get("description") or row.description or "")[:500]
                row.entity_type = entity_type
                row.metadata_ = {**(row.metadata_ or {}), **meta}
                updated += 1

            mirrored.append(
                {
                    "local_entity_id": local_id,
                    "remote_entity_id": remote_id,
                    "entity_type": entity_type.value,
                    "portable_id": portable,
                    "home_node_id": node_id,
                }
            )

    db.flush()
    return {
        "schema": "pocp.federation_entity_mirror.v0.1",
        "node_id": node_id,
        "peer_base_url": peer.base_url,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "mirrored_count": len(mirrored),
        "entities": mirrored[:50],
    }


def list_mirrored_entities(
    db: Session,
    *,
    home_node_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    q = db.query(Entity).filter(Entity.status == EntityStatus.active)
    rows = q.limit(500).all()
    out: list[dict[str, Any]] = []
    for row in rows:
        meta = row.metadata_ or {}
        if "federated_mirror" not in (meta.get("roles") or []):
            continue
        if home_node_id and meta.get("home_node_id") != home_node_id:
            continue
        out.append(
            {
                "entity_id": row.id,
                "name": row.name,
                "entity_type": row.entity_type.value,
                "home_node_id": meta.get("home_node_id"),
                "remote_entity_id": meta.get("remote_entity_id"),
                "portable_id": meta.get("portable_id"),
                "peer_base_url": meta.get("peer_base_url"),
            }
        )
        if len(out) >= limit:
            break
    return out


def append_federation_mirror_graph_edges(
    db: Session,
    *,
    edges: list[dict],
    entity_map: dict,
    append_edge,
) -> None:
    """Link federation peer nodes to locally mirrored remote entities."""
    for row in db.query(Entity).filter(Entity.status == EntityStatus.active).all():
        meta = row.metadata_ or {}
        roles = meta.get("roles") or []
        if "federated_mirror" not in roles:
            continue
        home = meta.get("home_node_id")
        if not home:
            continue
        peer_id = meta.get("peer_entity_id") or peer_entity_id(home)
        if peer_id not in entity_map or row.id not in entity_map:
            continue
        append_edge(
            edges,
            {
                "source": peer_id,
                "target": row.id,
                "relation": "mirrors_remote",
                "contribution_id": None,
                "weight": 0.65,
                "connection_layer": "protocol",
            },
        )


def resolve_mirror_for_dialogue(db: Session, local_entity_id: str) -> dict[str, Any] | None:
    """If entity is a remote mirror, return routing hints for dialogue."""
    row = db.get(Entity, local_entity_id)
    if not row:
        return None
    meta = row.metadata_ or {}
    if "federated_mirror" not in (meta.get("roles") or []):
        return None
    home = meta.get("home_node_id")
    if not home:
        return None
    return {
        "home_node_id": home,
        "remote_entity_id": meta.get("remote_entity_id"),
        "portable_id": meta.get("portable_id"),
        "peer_base_url": meta.get("peer_base_url"),
        "route_peer": True,
    }
