"""Persistent NodeProfile store — PR-05."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from models.capability import EntityCapability
from models.entity import Entity, EntityStatus
from models.node_profile import NodeMode, NodeProfileRecord, NodeStatus, NodeType
from services.capability.registry import descriptor_from_record


def _parse_node_type(value: str) -> NodeType:
    try:
        return NodeType(value)
    except ValueError as exc:
        raise ValueError(f"Invalid node_type: {value}") from exc


def _parse_node_mode(value: str | None) -> NodeMode:
    if not value:
        return NodeMode.hosted
    try:
        return NodeMode(value)
    except ValueError as exc:
        raise ValueError(f"Invalid node_mode: {value}") from exc


def _default_health_url(base_url: str | None) -> str | None:
    if not base_url:
        return None
    return f"{base_url.rstrip('/')}/pocp/health"


def _capability_types_for_entity(db: Session, entity_id: str) -> list[str]:
    rows = db.query(EntityCapability).filter(EntityCapability.entity_id == entity_id).all()
    return sorted({r.capability_type.value for r in rows})


def node_profile_to_dict(record: NodeProfileRecord, *, include_entity: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "node_id": record.id,
        "entity_id": record.entity_id,
        "node_type": record.node_type.value,
        "did": record.did,
        "public_key": record.public_key,
        "base_url": record.base_url,
        "p2p_address": record.p2p_address,
        "health_url": record.health_url,
        "node_mode": record.node_mode.value,
        "status": record.status.value,
        "protocol_version": record.protocol_version,
        "published_capabilities": list(record.published_capabilities or []),
        "metadata": dict(record.metadata_ or {}),
        "last_heartbeat_at": record.last_heartbeat_at.isoformat() if record.last_heartbeat_at else None,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }
    if include_entity and record.entity:
        payload["entity"] = {
            "entity_id": record.entity.id,
            "entity_type": record.entity.entity_type.value,
            "name": record.entity.name,
            "status": record.entity.status.value,
        }
    return payload


def build_public_endpoint_urls(record: NodeProfileRecord) -> dict[str, str] | None:
    if not record.base_url:
        return None
    base = record.base_url.rstrip("/")
    return {
        "base_url": base,
        "manifest_url": f"{base}/.well-known/pocp-node.json",
        "health_url": record.health_url or f"{base}/pocp/health",
        "capabilities_url": f"{base}/api/v1/registry/capabilities",
        "invoke_url": f"{base}/api/v1/invocations",
        "proof_url": f"{base}/api/v1/export/proof",
        "settlement_ack_url": f"{base}/api/v1/exchanges",
    }


def build_entity_node_manifest(db: Session, entity_id: str) -> dict[str, Any] | None:
    """Per-entity manifest for public discovery (complements instance-level manifest)."""
    entity = db.get(Entity, entity_id)
    if entity is None:
        return None
    record = get_node_by_entity(db, entity_id)
    caps = _capability_types_for_entity(db, entity_id)
    capability_items = []
    for row in (
        db.query(EntityCapability)
        .filter(EntityCapability.entity_id == entity_id)
        .order_by(EntityCapability.name)
        .all()
    ):
        desc = descriptor_from_record(row)
        capability_items.append(
            {
                "capability_id": desc.capability_id,
                "capability_type": desc.capability_type,
                "name": desc.name,
                "unit": desc.unit,
                "availability": desc.availability,
            }
        )
    base_url = (record.base_url if record else None) or os.getenv("BACKEND_URL", "http://127.0.0.1:8008").rstrip("/")
    return {
        "protocol_version": record.protocol_version if record else "pocp-node-v0.1",
        "manifest_kind": "entity_node",
        "node_id": record.id if record else f"node-entity-{entity_id[:8]}",
        "entity_id": entity_id,
        "entity_type": entity.entity_type.value,
        "name": entity.name,
        "base_url": base_url,
        "public_key": record.public_key if record else None,
        "capabilities_url": f"{base_url}/api/v1/registry/capabilities?entity_id={entity_id}",
        "health_url": f"{base_url}/health",
        "capabilities": capability_items,
        "published_capability_types": caps,
        "status": record.status.value if record else entity.status.value,
    }


def register_node(
    db: Session,
    *,
    entity_id: str,
    node_type: str,
    base_url: str | None = None,
    public_key: str | None = None,
    p2p_address: str | None = None,
    node_mode: str | None = None,
    node_id: str | None = None,
    published_capabilities: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> NodeProfileRecord:
    entity = db.get(Entity, entity_id)
    if entity is None:
        raise ValueError(f"Entity not found: {entity_id}")

    existing = (
        db.query(NodeProfileRecord).filter(NodeProfileRecord.entity_id == entity_id).first()
    )
    nt = _parse_node_type(node_type)
    nm = _parse_node_mode(node_mode)
    caps = published_capabilities if published_capabilities is not None else _capability_types_for_entity(
        db, entity_id
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if existing:
        existing.node_type = nt
        if base_url is not None:
            existing.base_url = base_url
            existing.health_url = _default_health_url(base_url)
        if public_key is not None:
            existing.public_key = public_key
        if p2p_address is not None:
            existing.p2p_address = p2p_address
        existing.node_mode = nm
        existing.status = NodeStatus.active
        existing.published_capabilities = caps
        if metadata:
            existing.metadata_ = {**(existing.metadata_ or {}), **metadata}
        existing.last_heartbeat_at = now
        existing.updated_at = now
        if not existing.did:
            existing.did = f"did:pocp:{entity_id}"
        db.flush()
        return existing

    nid = node_id or f"node-{uuid.uuid4().hex[:16]}"
    if len(nid) > 36:
        nid = str(uuid.uuid5(uuid.NAMESPACE_DNS, entity_id))
    profile = NodeProfileRecord(
        id=nid,
        entity_id=entity_id,
        node_type=nt,
        did=f"did:pocp:{entity_id}",
        public_key=public_key,
        base_url=base_url,
        p2p_address=p2p_address,
        health_url=_default_health_url(base_url),
        node_mode=nm,
        status=NodeStatus.active,
        published_capabilities=caps,
        metadata_=dict(metadata or {}),
        last_heartbeat_at=now,
    )
    db.add(profile)
    db.flush()
    return profile


def get_node(db: Session, node_id: str) -> NodeProfileRecord | None:
    return db.get(NodeProfileRecord, node_id)


def get_node_by_entity(db: Session, entity_id: str) -> NodeProfileRecord | None:
    return (
        db.query(NodeProfileRecord).filter(NodeProfileRecord.entity_id == entity_id).first()
    )


def record_heartbeat(db: Session, node_id: str) -> NodeProfileRecord:
    record = db.get(NodeProfileRecord, node_id)
    if record is None:
        raise ValueError("Node not found")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    record.last_heartbeat_at = now
    record.status = NodeStatus.active
    record.updated_at = now
    db.flush()
    return record


def discover_nodes(
    db: Session,
    *,
    capability_type: str | None = None,
    node_type: str | None = None,
    limit: int = 50,
) -> list[NodeProfileRecord]:
    query = (
        db.query(NodeProfileRecord)
        .join(Entity, Entity.id == NodeProfileRecord.entity_id)
        .filter(Entity.status == EntityStatus.active)
        .filter(NodeProfileRecord.status.in_([NodeStatus.registered, NodeStatus.active]))
    )
    if node_type:
        query = query.filter(NodeProfileRecord.node_type == _parse_node_type(node_type))
    rows = query.order_by(NodeProfileRecord.updated_at.desc()).limit(limit).all()
    if not capability_type:
        return rows
    filtered: list[NodeProfileRecord] = []
    for row in rows:
        published = row.published_capabilities or []
        if capability_type in published:
            filtered.append(row)
            continue
        if capability_type in _capability_types_for_entity(db, row.entity_id):
            filtered.append(row)
    return filtered
