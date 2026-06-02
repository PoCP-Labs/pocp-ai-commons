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
    peer_entity_id,
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
            f"{backend_url}/api/v1/intelligence/protocol/network",
            f"{backend_url}/api/v1/intelligence/network/overlay/status",
            f"{backend_url}/api/v1/intelligence/network/overlay/demo",
            f"{backend_url}/api/v1/intelligence/network/overlay/gossip/receive",
            f"{backend_url}/api/v1/intelligence/network/overlay/gossip/push",
            f"{backend_url}/api/v1/federation/overlay/status",
            f"{backend_url}/api/v1/federation/overlay/relay",
            f"{backend_url}/api/v1/federation/dialogue",
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


class RegisterPeerIn(BaseModel):
    node_id: str
    base_url: str
    trust_weight: float = 0.8
    public_key: str | None = None
    mirror_entities: bool = True


class AutoDiscoverPeersIn(BaseModel):
    candidate_urls: list[str] = Field(default_factory=list)
    include_localhost_scan: bool = True
    max_candidates: int = 20


def _discover_seed_urls() -> list[str]:
    raw = os.getenv("POCP_PEER_DISCOVERY_SEEDS", "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(v).strip() for v in parsed if str(v).strip()]
    except json.JSONDecodeError:
        pass
    return [v.strip() for v in raw.split(",") if v.strip()]


def _upsert_discovered_peer(
    db: Session,
    *,
    node_id: str,
    base_url: str,
    trust_weight: float | None = None,
    public_key: str | None = None,
) -> str:
    from models.entity import Entity, EntityStatus, EntityType

    entity_id = peer_entity_id(node_id)
    discovered = db.get(Entity, entity_id)
    discovered_meta = {
        "roles": ["federation_peer", "community", "discovered_peer"],
        "node_id": node_id,
        "base_url": base_url.rstrip("/"),
        "public_key": public_key,
        "trust_weight": trust_weight if trust_weight is not None else 0.7,
        "portable_id": f"pocp:federation:{node_id}",
        "registry": "discovered_register",
        "configured": False,
    }
    if discovered is None:
        discovered = Entity(
            id=entity_id,
            entity_type=EntityType.community,
            name=f"Federation Peer · {node_id}",
            description=f"Discovered federated PoCP node at {base_url.rstrip('/')}",
            status=EntityStatus.active,
            metadata_=discovered_meta,
        )
        db.add(discovered)
    else:
        discovered.entity_type = EntityType.community
        discovered.name = f"Federation Peer · {node_id}"
        discovered.description = f"Discovered federated PoCP node at {base_url.rstrip('/')}"[:500]
        discovered.metadata_ = {**(discovered.metadata_ or {}), **discovered_meta}
    return entity_id


@router.post("/peers/register")
def register_federation_peer(body: RegisterPeerIn, db: Session = Depends(get_db)):
    """
    Probe a public peer URL and mirror its entities locally.
    Persist trust by adding the same entry to POCP_TRUSTED_NODES or trusted_nodes.yaml.
    """
    from services.federation_community import ensure_federation_peer_entities
    from services.federation_entity_mirror import mirror_peer_entities

    probe = probe_peer(body.base_url)
    if not probe.get("reachable"):
        raise HTTPException(
            status_code=400,
            detail=probe.get("error") or "Peer not reachable",
        )

    trusted = load_trusted_nodes()
    known = {p.node_id: p for p in trusted}
    in_trust_list = body.node_id in known

    ensure_federation_peer_entities(db)
    discovered_entity_id = peer_entity_id(body.node_id)
    if not in_trust_list:
        discovered_entity_id = _upsert_discovered_peer(
            db,
            node_id=body.node_id,
            base_url=body.base_url,
            trust_weight=body.trust_weight,
            public_key=body.public_key,
        )
    mirror_summary = None
    if body.mirror_entities and in_trust_list:
        try:
            mirror_summary = mirror_peer_entities(db, body.node_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    elif body.mirror_entities and not in_trust_list:
        mirror_summary = {
            "skipped": True,
            "reason": "Add node to POCP_TRUSTED_NODES then call POST /peers/{node_id}/mirror-entities",
        }

    db.commit()
    return {
        "schema": "pocp.federation_peer_register.v0.1",
        "node_id": body.node_id,
        "base_url": body.base_url.rstrip("/"),
        "reachable": True,
        "in_trust_list": in_trust_list,
        "probe": probe,
        "mirror": mirror_summary,
        "trust_config_hint": (
            None
            if in_trust_list
            else {
                "env": "POCP_TRUSTED_NODES",
                "example": [
                    {
                        "node_id": body.node_id,
                        "base_url": body.base_url.rstrip("/"),
                        "trust_weight": body.trust_weight,
                        "public_key": body.public_key,
                    }
                ],
            }
        ),
    }


@router.post("/peers/auto-discover")
def auto_discover_peers(body: AutoDiscoverPeersIn, db: Session = Depends(get_db)):
    """
    Probe candidate URLs and auto-register reachable foreign PoCP nodes as discovered peers.
    Candidate sources:
    - request body candidate_urls
    - env POCP_PEER_DISCOVERY_SEEDS (JSON list or comma-separated URLs)
    - optional localhost port scan
    """
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    candidates: list[str] = []
    candidates.extend(body.candidate_urls or [])
    candidates.extend(_discover_seed_urls())
    if body.include_localhost_scan:
        for p in (8008, 8009, 8010, 8011, 8012, 8013):
            candidates.append(f"http://localhost:{p}")
    # normalize + de-dupe + cap
    norm: list[str] = []
    seen = set()
    for raw in candidates:
        url = str(raw).strip().rstrip("/")
        if not url or url in seen:
            continue
        seen.add(url)
        norm.append(url)
        if len(norm) >= max(1, min(body.max_candidates, 80)):
            break

    discovered: list[dict] = []
    failed: list[dict] = []
    for url in norm:
        if url == backend_url:
            continue
        probe = probe_peer(url)
        if not probe.get("reachable"):
            failed.append({"base_url": url, "error": probe.get("error")})
            continue
        node = probe.get("node") or {}
        node_id = node.get("node_id")
        if not node_id or node_id == _NODE_ID:
            continue
        entity_id = _upsert_discovered_peer(
            db,
            node_id=node_id,
            base_url=url,
            public_key=node.get("public_key"),
        )
        discovered.append(
            {
                "node_id": node_id,
                "base_url": url,
                "entity_id": entity_id,
                "ledger_valid": probe.get("ledger_valid"),
                "ledger_count": probe.get("ledger_count"),
            }
        )

    db.commit()
    return {
        "schema": "pocp.federation_auto_discover.v0.1",
        "local_node_id": _NODE_ID,
        "scanned": len(norm),
        "discovered_count": len(discovered),
        "discovered": discovered,
        "failed": failed[:20],
    }


@router.post("/peers/{node_id}/mirror-entities")
def mirror_peer_entities_endpoint(node_id: str, db: Session = Depends(get_db)):
    from services.federation_entity_mirror import mirror_peer_entities

    try:
        result = mirror_peer_entities(db, node_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return result


@router.get("/peers/{node_id}/remote-entities")
def list_peer_remote_entities(node_id: str, limit: int = 100, db: Session = Depends(get_db)):
    from services.federation_entity_mirror import list_mirrored_entities

    return {
        "node_id": node_id,
        "entities": list_mirrored_entities(db, home_node_id=node_id, limit=limit),
    }


@router.get("/peers/entities")
def federation_peer_entities(db: Session = Depends(get_db)):
    """Community entities representing local and trusted federation peer nodes."""
    entities = list_federation_peer_entities(db)
    db.commit()
    return {
        "compat": "pocp.federation_community.v0.1",
        "local_node_id": _NODE_ID,
        "peer_count": len([e for e in entities if not e.get("is_local")]),
        "entities": entities,
    }


@router.get("/network/overview")
def federation_network_overview(
    satellite_limit: int = Query(default=36, ge=0, le=120),
    db: Session = Depends(get_db),
):
    """Unified federation topology for AI Node mini-map (nodes + mirrors + edges)."""
    from services.federation_network import build_federation_network_overview

    return build_federation_network_overview(db, satellite_limit=satellite_limit)


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


class FederationOverlayRelayIn(BaseModel):
    """PN-4: Pull proof from trusted peer, validate, enqueue overlay event, optional import."""

    source_node_id: str
    contribution_id: str | None = None
    proof: dict | None = None
    auto_import: bool = False


@router.get("/overlay/status")
def federation_overlay_status_endpoint():
    from services.network.runtime import federation_overlay_status

    return federation_overlay_status()


@router.post("/overlay/relay")
def federation_overlay_relay(body: FederationOverlayRelayIn, db: Session = Depends(get_db)):
    from services.network.federation_overlay import relay_federation_offer

    try:
        result = relay_federation_offer(
            db,
            source_node_id=body.source_node_id,
            contribution_id=body.contribution_id,
            proof=body.proof,
            auto_import=body.auto_import,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if body.auto_import and result.get("import"):
        db.commit()
    return result


@router.post("/dialogue")
async def federation_dialogue(envelope: dict, db: Session = Depends(get_db)):
    """Entity Dialogue entrypoint on federation surface (same router as overlay relay)."""
    from services.entity_dialogue import route_dialogue

    return await route_dialogue(db, envelope)
