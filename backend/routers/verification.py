from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.contribution import ContributionEvent, ContributionStatus
from models.user_account import UserAccount
from routers.auth import require_current_user
from intelligence import capability_layer
from services.clarion import build_clarion_review_packet
from services.contribution_dispute import (
    appeal_dispute,
    challenge_contribution,
    dispute_evidence_digest,
    list_disputes,
    resolve_open_disputes,
)
from services.contribution_verification_network import (
    build_verification_network_manifest,
    resolve_verifier_node,
)
from services.finalization import build_verdict_snapshot
from services.verify_standalone import verify_proof_integrity

router = APIRouter(prefix="/api/v1", tags=["verification"])


class ChallengeIn(BaseModel):
    reason: str = Field(min_length=8, max_length=2000)
    evidence: dict | None = None


class AppealIn(BaseModel):
    reason: str = Field(min_length=8, max_length=2000)
    parent_dispute_id: str | None = None


class ResolveDisputeIn(BaseModel):
    reviewer_id: str
    upheld: bool
    feedback: str | None = None


class ProofVerifyIn(BaseModel):
    proof: dict
    trusted_public_key: str | None = None
    require_signature: bool = False


class DisputeEvidenceDigestIn(BaseModel):
    evidence: dict


@router.get("/verification/network")
def verification_network_manifest(db: Session = Depends(get_db)):
    """CI-8 sketch — verification network manifest for standalone verifier nodes."""
    return build_verification_network_manifest(db)


@router.get("/verification/verifier-node")
def default_verifier_node_manifest(db: Session = Depends(get_db)):
    """CI-8 sketch — default local verifier_node wiring."""
    snapshot = resolve_verifier_node(db)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Default verifier_node not registered")
    return snapshot


@router.get("/verification/verifier-node/{entity_id}")
def verifier_node_manifest(entity_id: str, db: Session = Depends(get_db)):
    """CI-8 sketch — per-entity verifier_node manifest."""
    snapshot = resolve_verifier_node(db, entity_id=entity_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Verifier node not found or inactive")
    return snapshot


@router.post("/verification/proof/verify")
def verification_proof_verify(body: ProofVerifyIn):
    """CI-8 sketch — offline proof verify (mirrors export; no DB trust)."""
    return verify_proof_integrity(
        body.proof,
        trusted_public_key=body.trusted_public_key,
        require_signature=body.require_signature,
    )


@router.post("/verification/disputes/evidence/digest")
def verification_dispute_evidence_digest(body: DisputeEvidenceDigestIn):
    """CI-8 sketch — stable digest for dispute evidence bundles."""
    return {"digest": dispute_evidence_digest(body.evidence)}


@router.post("/contributions/{contribution_id}/auto-verify")
async def auto_verify_contribution(
    contribution_id: str,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    contribution = (
        db.query(ContributionEvent)
        .options(joinedload(ContributionEvent.task), joinedload(ContributionEvent.participants))
        .filter(ContributionEvent.id == contribution_id)
        .first()
    )
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    if contribution.primary_entity_id != current_user.entity_id:
        raise HTTPException(status_code=403, detail="Only the contribution owner can request auto verification")
    if contribution.status not in (ContributionStatus.submitted, ContributionStatus.draft):
        raise HTTPException(status_code=400, detail=f"Cannot verify contribution in status: {contribution.status.value}")
    consensus = await capability_layer.verify_contribution(db, contribution)
    db.commit()
    db.refresh(contribution)
    verdict = build_verdict_snapshot(contribution)
    return {
        "contribution_id": contribution.id,
        "status": contribution.status.value,
        "consensus": consensus,
        "language_hint": consensus.get("language_hint"),
        "verdict": verdict,
        "finalization": consensus.get("finalization"),
    }


@router.get("/contributions/{contribution_id}/verdict")
def contribution_verdict(
    contribution_id: str,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Maestro-style verdict inspect — PASS / ESCALATE / FAIL with decision_id."""
    contribution = (
        db.query(ContributionEvent)
        .options(
            joinedload(ContributionEvent.ai_verifications),
            joinedload(ContributionEvent.participants),
        )
        .filter(ContributionEvent.id == contribution_id)
        .first()
    )
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    participant_ids = {p.entity_id for p in contribution.participants}
    if current_user.entity_id not in participant_ids and current_user.entity_id != contribution.primary_entity_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this verdict")
    return build_verdict_snapshot(contribution)


@router.get("/contributions/{contribution_id}/clarion-review")
def clarion_review_contribution(
    contribution_id: str,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    contribution = (
        db.query(ContributionEvent)
        .options(
            joinedload(ContributionEvent.task),
            joinedload(ContributionEvent.participants),
            joinedload(ContributionEvent.ai_verifications),
            joinedload(ContributionEvent.human_reviews),
        )
        .filter(ContributionEvent.id == contribution_id)
        .first()
    )
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")

    participant_ids = {p.entity_id for p in contribution.participants}
    if current_user.entity_id not in participant_ids and current_user.entity_id != contribution.primary_entity_id:
        raise HTTPException(
            status_code=403,
            detail="Only contribution participants can request a Clarion-0 review packet",
        )

    return build_clarion_review_packet(db, contribution)


@router.get("/contributions/{contribution_id}/disputes")
def contribution_disputes(
    contribution_id: str,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    contribution = db.query(ContributionEvent).filter(ContributionEvent.id == contribution_id).first()
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    return {"contribution_id": contribution_id, "disputes": list_disputes(db, contribution_id)}


@router.post("/contributions/{contribution_id}/challenge")
def challenge_contribution_endpoint(
    contribution_id: str,
    body: ChallengeIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    contribution = (
        db.query(ContributionEvent)
        .options(joinedload(ContributionEvent.participants))
        .filter(ContributionEvent.id == contribution_id)
        .first()
    )
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    dispute = challenge_contribution(
        db,
        contribution,
        challenger_entity_id=current_user.entity_id,
        reason=body.reason,
        evidence=body.evidence,
    )
    db.commit()
    return {
        "contribution_id": contribution.id,
        "status": contribution.status.value,
        "dispute": {
            "id": dispute.id,
            "kind": dispute.kind.value,
            "status": dispute.status.value,
            "evidence_hash": dispute.evidence_hash,
        },
    }


@router.post("/contributions/{contribution_id}/appeal")
def appeal_contribution_endpoint(
    contribution_id: str,
    body: AppealIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    contribution = db.query(ContributionEvent).filter(ContributionEvent.id == contribution_id).first()
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    dispute = appeal_dispute(
        db,
        contribution,
        appellant_entity_id=current_user.entity_id,
        reason=body.reason,
        parent_dispute_id=body.parent_dispute_id,
    )
    db.commit()
    return {
        "contribution_id": contribution.id,
        "status": contribution.status.value,
        "dispute": {
            "id": dispute.id,
            "kind": dispute.kind.value,
            "status": dispute.status.value,
            "parent_dispute_id": dispute.parent_dispute_id,
        },
    }


@router.post("/contributions/{contribution_id}/resolve-dispute")
def resolve_dispute_endpoint(
    contribution_id: str,
    body: ResolveDisputeIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Human finalization on appealed contributions — uphold or dismiss challenge."""
    if body.reviewer_id != current_user.entity_id:
        raise HTTPException(status_code=403, detail="reviewer_id must match authenticated entity")
    contribution = db.query(ContributionEvent).filter(ContributionEvent.id == contribution_id).first()
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    if contribution.status != ContributionStatus.appealed:
        raise HTTPException(status_code=400, detail="Contribution must be in appealed status")

    resolve_open_disputes(
        db,
        contribution,
        resolver_entity_id=body.reviewer_id,
        upheld=body.upheld,
        note=body.feedback,
    )
    contribution.status = ContributionStatus.rejected if body.upheld else ContributionStatus.approved
    db.commit()
    return {
        "contribution_id": contribution.id,
        "status": contribution.status.value,
        "challenge_upheld": body.upheld,
        "disputes": list_disputes(db, contribution_id),
    }
