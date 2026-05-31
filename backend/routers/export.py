from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.entity import Entity
from models.ledger import LedgerRecord
from models.wallet import CreditTransaction, ReputationScore, Wallet
from schemas import EntityOut, LedgerOut
from services.ledger_chain import verify_ledger_chain
from services.ledger_anchor import build_ledger_anchor, build_ledger_inclusion_proof
from services.graph_merkle import (
    build_graph_delta,
    build_graph_inclusion_from_db,
    build_graph_merkle_state,
)
from services.ledger_merkle import merkle_root
from services.pow_export import build_pow_export
from services.proof import build_contribution_proof_packet
from services.protocol_config import get_rewards_config
from services.issuance_budget import issuance_budget_status
from services.verify_standalone import audit_remote_node, verify_ledger_export, verify_proof_integrity
from services.wallet_audit import audit_all_wallets, audit_wallet_by_entity, verify_wallet_export

router = APIRouter(prefix="/api/v1", tags=["export"])


class LedgerVerifyOut(BaseModel):
    valid: bool
    count: int
    verified_count: int = 0
    first_broken_id: str | None = None
    genesis_hash: str | None = None
    tip_hash: str | None = None
    merkle_root: str | None = None


class ProofVerifyIn(BaseModel):
    proof: dict
    trusted_public_key: str | None = None
    require_signature: bool = False


class ProofVerifyOut(BaseModel):
    valid: bool
    proof_id: str | None = None
    contribution_id: str | None = None
    exchange_id: str | None = None
    checks: list[dict] = Field(default_factory=list)
    ledger_subchain: dict | None = None


class NodeAuditOut(BaseModel):
    base_url: str
    valid: bool
    node_id: str | None = None
    verify: dict | None = None
    anchor: dict | None = None
    checks: list[dict] = Field(default_factory=list)
    error: str | None = None


class LedgerExportVerifyOut(BaseModel):
    export_valid: bool
    valid: bool
    count: int
    merkle_root: str | None = None
    genesis_hash: str | None = None
    tip_hash: str | None = None


class WalletAuditOut(BaseModel):
    valid: bool
    wallet_count: int
    invalid_count: int
    wallets: list[dict] = Field(default_factory=list)
    audit_model: str = "transaction_replay_v0.1"


class WalletExportOut(BaseModel):
    spec_version: str
    exported_at: datetime
    wallets: list[dict]
    transactions: list[dict]


class LedgerExportOut(BaseModel):
    spec_version: str
    exported_at: datetime
    records: list[LedgerOut]


class PortableEntityOut(BaseModel):
    spec_version: str
    entity: EntityOut
    portable_id: str | None = None
    external_ids: dict[str, str] = Field(default_factory=dict)
    wallet: dict | None = None
    reputation: list[dict] = Field(default_factory=list)


class ContributionProofOut(BaseModel):
    model_config = {"extra": "allow"}

    spec_version: str
    proof_type: str
    proof_schema: str
    proof_id: str
    generated_at: datetime
    protocol_layers: list[str]
    contribution_event: dict
    entity_identity: dict
    evidence: dict
    verification: dict
    contribution_graph: dict
    rights_and_reputation: dict
    ledger_audit: dict
    integrity: dict
    federation: dict | None = None
    expert_cards: list | None = None
    code_attribution_context: dict | None = None
    attribution_merkle_proof: dict | None = None
    external_inspirations_context: dict | None = None
    finalization: dict | None = None
    invocation_trace: dict | None = None


class LedgerAnchorOut(BaseModel):
    spec_version: str
    anchor_type: str
    node_id: str
    anchored_at: str
    record_count: int
    merkle_root: str
    graph_merkle_root: str | None = None
    graph_edge_count: int = 0
    graph_algorithm: str | None = None
    hash_algorithm: str | None = None
    ledger_valid: bool
    ledger_record_count: int
    tip_hash: str | None = None
    federation: dict | None = None
    peer_attestations: list[dict] | None = None
    cosign_summary: dict | None = None


@router.get("/ledger/verify", response_model=LedgerVerifyOut)
def verify_ledger(db: Session = Depends(get_db)):
    result = verify_ledger_chain(db)
    hashes = []
    if result.get("valid") and result.get("count", 0) > 0:
        records = (
            db.query(LedgerRecord)
            .filter(LedgerRecord.record_hash.isnot(None))
            .order_by(LedgerRecord.created_at.asc(), LedgerRecord.id.asc())
            .all()
        )
        hashes = [r.record_hash for r in records if r.record_hash]
    result["merkle_root"] = merkle_root(hashes) if hashes else None
    return result


@router.post("/proof/verify", response_model=ProofVerifyOut)
def verify_proof_body(body: ProofVerifyIn):
    """Verify an exported contribution proof without database access."""
    return verify_proof_integrity(
        body.proof,
        trusted_public_key=body.trusted_public_key,
        require_signature=body.require_signature,
    )


@router.post("/ledger/export/verify", response_model=LedgerExportVerifyOut)
def verify_ledger_export_body(export: dict):
    """Verify a previously exported ledger bundle (offline audit friendly)."""
    return verify_ledger_export(export)


@router.get("/issuance/budget")
def get_issuance_budget(db: Session = Depends(get_db)):
    """Daily CP / AI Credits issuance caps and remaining budget (Bitcoin-style discipline)."""
    return issuance_budget_status(db)


@router.get("/audit/node", response_model=NodeAuditOut)
def audit_node(
    url: str = Query(..., description="Base URL of PoCP node to audit"),
):
    """Public audit: fetch verify + anchor from a remote node and cross-check."""
    return audit_remote_node(url)


@router.get("/wallets/audit", response_model=WalletAuditOut)
def audit_wallets(db: Session = Depends(get_db)):
    """Recompute all wallet balances from credit_transactions — detect silent minting."""
    return audit_all_wallets(db)


@router.get("/wallets/{entity_id}/audit")
def audit_wallet(entity_id: str, db: Session = Depends(get_db)):
    result = audit_wallet_by_entity(db, entity_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return result


@router.get("/wallets/export", response_model=WalletExportOut)
def export_wallets(db: Session = Depends(get_db)):
    """Export wallets + transactions for offline balance audit."""
    wallets = db.query(Wallet).order_by(Wallet.entity_id.asc()).all()
    txs = db.query(CreditTransaction).order_by(CreditTransaction.created_at.asc()).all()
    return WalletExportOut(
        spec_version=get_rewards_config().get("spec_version", "0.1"),
        exported_at=datetime.utcnow(),
        wallets=[
            {
                "id": w.id,
                "entity_id": w.entity_id,
                "cp_balance": w.cp_balance,
                "ai_credits": w.ai_credits,
            }
            for w in wallets
        ],
        transactions=[
            {
                "id": t.id,
                "wallet_id": t.wallet_id,
                "contribution_id": t.contribution_id,
                "amount": t.amount,
                "credit_type": t.credit_type.value,
                "reason": t.reason,
                "created_at": t.created_at.isoformat(),
            }
            for t in txs
        ],
    )


@router.post("/wallets/export/verify", response_model=WalletAuditOut)
def verify_wallet_export_body(export: dict):
    return verify_wallet_export(export)


@router.get("/ledger/merkle-proof/{record_hash}")
def get_ledger_merkle_proof(record_hash: str, db: Session = Depends(get_db)):
    """SPV-style Merkle inclusion proof for one ledger record hash."""
    bundle = build_ledger_inclusion_proof(db, record_hash)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Record hash not found in ledger")
    return bundle


@router.get("/graph/merkle-root")
def get_graph_merkle_root(db: Session = Depends(get_db)):
    """Current Contribution Graph Merkle root (canonical edge commitment)."""
    from services.graph import build_contribution_graph

    graph = build_contribution_graph(db)
    return build_graph_merkle_state(graph["edges"])


@router.get("/graph/merkle-proof/contribution/{contribution_id}")
def get_contribution_graph_merkle_proof(contribution_id: str, db: Session = Depends(get_db)):
    """SPV-style Merkle inclusion proofs for all edges of one contribution."""
    bundle = build_graph_inclusion_from_db(db, contribution_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Contribution not found in graph")
    return bundle


@router.get("/ledger/anchor", response_model=LedgerAnchorOut)
def get_ledger_anchor(
    db: Session = Depends(get_db),
    skip_cosign: bool = Query(default=False, description="Skip peer cosign fetch (avoids federation recursion)"),
):
    return build_ledger_anchor(db, skip_cosign=skip_cosign)


@router.get("/ledger/export", response_model=LedgerExportOut)
def export_ledger(
    since: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(LedgerRecord).order_by(LedgerRecord.created_at.asc(), LedgerRecord.id.asc())
    if since is not None:
        query = query.filter(LedgerRecord.created_at >= since)
    records = query.all()
    return LedgerExportOut(
        spec_version=get_rewards_config().get("spec_version", "0.1"),
        exported_at=datetime.utcnow(),
        records=records,
    )


@router.get("/entities/{entity_id}/portable", response_model=PortableEntityOut)
def get_portable_entity(entity_id: str, db: Session = Depends(get_db)):
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    metadata = entity.metadata_ or {}
    external_ids = dict(metadata.get("external_ids") or {})
    portable_id = metadata.get("portable_id")
    if not portable_id and metadata.get("provider") and metadata.get("provider_user_id"):
        portable_id = f"{metadata['provider']}:{metadata['provider_user_id']}"

    wallet = db.query(Wallet).filter(Wallet.entity_id == entity_id).first()
    reputation = db.query(ReputationScore).filter(ReputationScore.entity_id == entity_id).all()

    return PortableEntityOut(
        spec_version=get_rewards_config().get("spec_version", "0.1"),
        entity=entity,
        portable_id=portable_id,
        external_ids=external_ids,
        wallet={
            "cp_balance": wallet.cp_balance,
            "ai_credits": wallet.ai_credits,
        }
        if wallet
        else None,
        reputation=[
            {"category": r.category, "score": r.score, "updated_at": r.updated_at.isoformat()}
            for r in reputation
        ],
    )


@router.get("/contributions/{contribution_id}/proof", response_model=ContributionProofOut)
def get_contribution_proof(contribution_id: str, db: Session = Depends(get_db)):
    packet = build_contribution_proof_packet(db, contribution_id)
    if packet is None:
        raise HTTPException(status_code=404, detail="Contribution not found")
    return packet


@router.get("/contributions/{contribution_id}/pow")
def get_contribution_pow_export(contribution_id: str, db: Session = Depends(get_db)):
    """Export contribution proof as pow.yaml-compatible interop record (PoC Protocol Core)."""
    result = build_pow_export(db, contribution_id)
    if result.get("pow_record") is None:
        raise HTTPException(status_code=404, detail="Contribution not found")
    return result
