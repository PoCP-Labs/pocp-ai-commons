import json
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.federation import FederatedImport
from schemas.federation import (
    FederationNodeOut,
    FederationSettlementIntentIn,
    ImportEventPayload,
    TrustListOut,
    TrustedNode,
)
from services.federation_crypto import get_node_public_key_hex
from services.crypto_suite import active_crypto_suite, get_node_pqc_public_key_hex
from services.federation_import import import_federated_event, import_from_proof_packet
from services.federation_peers import probe_peer
from services.federation_reputation import get_federated_reputation
from services.federation_sync import sync_all_trusted_peers
from services.federation_settlement import apply_settlement_intent, list_federation_settlements
from services.federation_community import (
    federation_import_graph_summary,
    list_entity_federation_imports,
    list_federation_peer_entities,
    list_peer_node_imports,
)
from services.node_mode import node_mode
from services.trust_config import load_trusted_nodes, trust_list_hash, trusted_nodes_source
from services.trust_policy_bundle import (
    trust_policy_bundle_manifest,
    validate_proof_against_trust_policy,
)

router = APIRouter(prefix="/api/v1/federation", tags=["federation"])

_NODE_ID = os.getenv("POCP_NODE_ID", f"pocp-node-{uuid.uuid4().hex[:8]}")
_SPEC_VERSION = "0.1"


class ImportProofIn(BaseModel):
    source_node_id: str
    proof: dict


class ImportExchangeProofIn(BaseModel):
    source_node_id: str
    proof: dict
    acceptance_level: str = "L1"


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
        pqc_public_key=get_node_pqc_public_key_hex(),
        crypto_suite=active_crypto_suite(),
        node_mode=node_mode(),
        public_endpoints=[
            f"{backend_url}/api/v1/ledger/export",
            f"{backend_url}/api/v1/entities/{{id}}/portable",
            f"{backend_url}/api/v1/contributions/{{id}}/proof",
            f"{backend_url}/api/v1/ledger/verify",
            f"{backend_url}/api/v1/ledger/anchor",
            f"{backend_url}/api/v1/crypto/readiness",
            f"{backend_url}/api/v1/crypto/suites",
            f"{backend_url}/api/v1/federation/imports",
            f"{backend_url}/api/v1/federation/reputation?portable_id={{portable_id}}",
            f"{backend_url}/api/v1/federation/peers/health",
            f"{backend_url}/api/v1/federation/sync",
            f"{backend_url}/api/v1/federation/trust-policy-bundle",
            f"{backend_url}/api/v1/federation/validate-proof",
            f"{backend_url}/api/v1/federation/settlement/intent",
            f"{backend_url}/api/v1/federation/settlements",
            f"{backend_url}/api/v1/intelligence/federation/export/{{contribution_id}}",
            f"{backend_url}/api/v1/intelligence/protocol",
            f"{backend_url}/api/v1/intelligence/protocol/entity-dialogue",
            f"{backend_url}/api/v1/intelligence/dialogue",
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


@router.get("/peers/entities")
def federation_peer_entities(db: Session = Depends(get_db)):
    """Community entities representing local and trusted federation peer nodes."""
    entities = list_federation_peer_entities(db)
    return {
        "compat": "pocp.federation_community.v0.1",
        "local_node_id": _NODE_ID,
        "peer_count": len([e for e in entities if not e.get("is_local")]),
        "entities": entities,
    }


@router.get("/imports/graph-summary")
def federated_imports_graph_summary(db: Session = Depends(get_db)):
    return {
        "compat": "pocp.federation_import_graph.v0.1",
        **federation_import_graph_summary(db),
    }


@router.get("/peers/{node_id}/imports")
def peer_node_imports(node_id: str, limit: int = 50, db: Session = Depends(get_db)):
    return list_peer_node_imports(db, node_id, limit=limit)


@router.get("/entities/{entity_id}/imports")
def entity_federation_imports(entity_id: str, limit: int = 50, db: Session = Depends(get_db)):
    from models.entity import Entity

    entity = db.get(Entity, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return list_entity_federation_imports(db, entity_id, limit=limit)


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


@router.get("/trust-policy-bundle")
def get_trust_policy_bundle():
    """Active trust + finalization + entity-connection + import rules for this node."""
    return trust_policy_bundle_manifest()


class ValidateProofIn(BaseModel):
    source_node_id: str | None = None
    proof: dict


@router.post("/validate-proof")
def validate_proof_endpoint(body: ValidateProofIn):
    """Dry-run trust policy validation without importing."""
    return validate_proof_against_trust_policy(
        body.proof,
        source_node_id=body.source_node_id,
        raise_on_block=False,
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


@router.post("/import-exchange-proof", response_model=FederatedImportOut, status_code=201)
def import_exchange_proof_endpoint(body: ImportExchangeProofIn, db: Session = Depends(get_db)):
    """L1 federation import for portable exchange proofs (verify-only, no BC mint)."""
    from services.federation_exchange_import import import_federated_exchange_proof

    record = import_federated_exchange_proof(
        db,
        body.source_node_id,
        body.proof,
        acceptance_level=body.acceptance_level,
    )
    db.commit()
    db.refresh(record)
    return record


@router.post("/settlement/intent")
def federation_settlement_intent(body: FederationSettlementIntentIn, db: Session = Depends(get_db)):
    """Apply mirrored provider credit from a trusted consumer node's signed intent."""
    try:
        result = apply_settlement_intent(db, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return result


@router.get("/settlements")
def federation_settlements(
    side: str | None = None,
    status: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List local federation settlement ledger entries (consumer debits or provider credits)."""
    return list_federation_settlements(db, side=side, status=status, limit=limit)
