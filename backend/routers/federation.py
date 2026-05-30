import json
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.federation import FederatedImport
from schemas.federation import FederationNodeOut, ImportEventPayload, TrustListOut, TrustedNode
from services.federation_crypto import get_node_public_key_hex
from services.federation_import import import_federated_event, import_from_proof_packet
from services.federation_peers import probe_peer
from services.federation_reputation import get_federated_reputation
from services.federation_sync import sync_all_trusted_peers
from services.node_mode import node_mode
from services.trust_config import load_trusted_nodes, trust_list_hash, trusted_nodes_source

router = APIRouter(prefix="/api/v1/federation", tags=["federation"])

_NODE_ID = os.getenv("POCP_NODE_ID", f"pocp-node-{uuid.uuid4().hex[:8]}")
_SPEC_VERSION = "0.1"


class ImportProofIn(BaseModel):
    source_node_id: str
    proof: dict


class FederatedImportOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    source_node_id: str
    source_contribution_id: str
    primary_entity_id: str
    primary_portable_id: str
    task_title: str
    contribution_type: str
    evidence_hash: str
    ledger_record_hash: str | None = None
    trust_weight: float
    reputation_applied: float
    imported_at: datetime


def _trusted_nodes() -> list[TrustedNode]:
    return load_trusted_nodes()


@router.get("/node", response_model=FederationNodeOut)
def get_node_info():
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    return FederationNodeOut(
        node_id=_NODE_ID,
        spec_version=_SPEC_VERSION,
        public_key=get_node_public_key_hex(),
        node_mode=node_mode(),
        public_endpoints=[
            f"{backend_url}/api/v1/ledger/export",
            f"{backend_url}/api/v1/entities/{{id}}/portable",
            f"{backend_url}/api/v1/contributions/{{id}}/proof",
            f"{backend_url}/api/v1/ledger/verify",
            f"{backend_url}/api/v1/ledger/anchor",
            f"{backend_url}/api/v1/federation/imports",
            f"{backend_url}/api/v1/federation/reputation?portable_id={{portable_id}}",
            f"{backend_url}/api/v1/federation/peers/health",
            f"{backend_url}/api/v1/federation/sync",
        ],
    )


class SyncOut(BaseModel):
    peers_checked: int
    imported: int
    skipped: int
    errors: int
    peer_health: list[dict] = Field(default_factory=list)
    results: list[dict] = Field(default_factory=list)


@router.get("/peers/health")
def peers_health():
    peers = load_trusted_nodes()
    return {
        "local_node_id": _NODE_ID,
        "peer_count": len(peers),
        "peers": [{"node_id": p.node_id, "trust_weight": p.trust_weight, **probe_peer(p.base_url)} for p in peers],
    }


@router.post("/sync", response_model=SyncOut)
def sync_trusted_peers(db: Session = Depends(get_db)):
    """Pull and import approved proofs from all POCP_TRUSTED_NODES into this node."""
    if not load_trusted_nodes():
        raise HTTPException(status_code=400, detail="No trusted nodes configured")
    return sync_all_trusted_peers(db)


@router.get("/trust", response_model=TrustListOut)
def get_trust_list():
    nodes = load_trusted_nodes()
    return TrustListOut(
        trusted_nodes=nodes,
        source=trusted_nodes_source(),
        trust_list_hash=trust_list_hash(nodes) if nodes else None,
    )


@router.get("/reputation")
def federated_reputation(portable_id: str = Query(...), db: Session = Depends(get_db)):
    return get_federated_reputation(db, portable_id)


@router.get("/imports", response_model=list[FederatedImportOut])
def list_federated_imports(db: Session = Depends(get_db)):
    return (
        db.query(FederatedImport)
        .order_by(FederatedImport.imported_at.desc())
        .all()
    )


@router.post("/import", response_model=FederatedImportOut, status_code=201)
def import_federated_event_endpoint(body: ImportEventPayload, db: Session = Depends(get_db)):
    record = import_federated_event(db, body)
    db.commit()
    db.refresh(record)
    return record


@router.post("/import-proof", response_model=FederatedImportOut, status_code=201)
def import_proof_endpoint(body: ImportProofIn, db: Session = Depends(get_db)):
    record = import_from_proof_packet(db, body.source_node_id, body.proof)
    db.commit()
    db.refresh(record)
    return record
