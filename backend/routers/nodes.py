"""Node profile API — register, heartbeat, discover (PR-05)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.user_account import UserAccount
from routers.auth import require_current_user
from services.entity_management import assert_entity_governable_by_actor
from services.node.store import (
    build_entity_node_manifest,
    build_public_endpoint_urls,
    discover_nodes,
    get_node,
    node_profile_to_dict,
    record_heartbeat,
    register_node,
)

router = APIRouter(prefix="/api/v1/nodes", tags=["nodes"])


class NodeRegisterIn(BaseModel):
    entity_id: str
    node_type: str
    base_url: str | None = None
    public_key: str | None = None
    p2p_address: str | None = None
    node_mode: str | None = "hosted"
    node_id: str | None = None
    published_capabilities: list[str] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NodeOut(BaseModel):
    node_id: str
    entity_id: str
    node_type: str
    did: str | None = None
    public_key: str | None = None
    base_url: str | None = None
    p2p_address: str | None = None
    health_url: str | None = None
    node_mode: str
    status: str
    protocol_version: str
    published_capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    public_endpoints: dict[str, str] | None = None


def _to_out(record) -> NodeOut:
    data = node_profile_to_dict(record)
    endpoints = build_public_endpoint_urls(record)
    return NodeOut(
        node_id=data["node_id"],
        entity_id=data["entity_id"],
        node_type=data["node_type"],
        did=data.get("did"),
        public_key=data.get("public_key"),
        base_url=data.get("base_url"),
        p2p_address=data.get("p2p_address"),
        health_url=data.get("health_url"),
        node_mode=data["node_mode"],
        status=data["status"],
        protocol_version=data["protocol_version"],
        published_capabilities=data.get("published_capabilities") or [],
        metadata=data.get("metadata") or {},
        public_endpoints=endpoints,
    )


@router.post("/register", status_code=201)
def register_node_endpoint(
    body: NodeRegisterIn,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(require_current_user),
):
    assert_entity_governable_by_actor(db, body.entity_id, user.entity_id)
    try:
        record = register_node(
            db,
            entity_id=body.entity_id,
            node_type=body.node_type,
            base_url=body.base_url,
            public_key=body.public_key,
            p2p_address=body.p2p_address,
            node_mode=body.node_mode,
            node_id=body.node_id,
            published_capabilities=body.published_capabilities,
            metadata=body.metadata,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(record)


@router.get("/discover")
def discover_nodes_endpoint(
    capability_type: str | None = Query(default=None),
    node_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    rows = discover_nodes(
        db, capability_type=capability_type, node_type=node_type, limit=limit
    )
    return {
        "count": len(rows),
        "items": [
            {**node_profile_to_dict(r, include_entity=True), "public_endpoints": build_public_endpoint_urls(r)}
            for r in rows
        ],
    }


@router.get("/{node_id}")
def get_node_endpoint(node_id: str, db: Session = Depends(get_db)):
    record = get_node(db, node_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return _to_out(record)


@router.post("/{node_id}/heartbeat")
def heartbeat_endpoint(node_id: str, db: Session = Depends(get_db)):
    try:
        record = record_heartbeat(db, node_id)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_out(record)


entity_router = APIRouter(prefix="/api/v1/entities", tags=["nodes"])


@entity_router.get("/{entity_id}/node-manifest")
def entity_node_manifest(entity_id: str, db: Session = Depends(get_db)):
    manifest = build_entity_node_manifest(db, entity_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return manifest
