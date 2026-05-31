from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.contribution import ContributionEvent
from models.entity import Entity, EntityType
from models.user_account import UserAccount
from routers.auth import require_current_user
from schemas import AgentFeedbackIn, AgentFeedbackOut, AgentReputationSummary
from services.agent_receipt import build_agent_receipt, load_trace_for_receipt, verify_agent_receipt
from services.agent_reputation import AgentReputationError, get_agent_reputation_summary, give_agent_feedback, list_agent_clients
from services.attribution_merkle import build_attribution_merkle_proof, verify_attribution_merkle_proof
from services.code_attribution_bridge import build_code_attribution_context
from services.evidence_validate import validate_evidence_full
from services.expert_cards import expert_cards_from_contribution
from services.external_inspiration import get_inspirations_for_contribution
from services.community_partner import get_contribution_partner_context
from services.federation_community import get_contribution_federation_context
from services.portable_reputation import (
    build_portable_reputation_by_id,
    build_portable_reputation_by_portable_id,
)
from services.reputation_audit import list_reputation_audit
from services.review_queue import list_human_review_queue
from services.reward_advisory import build_reward_advisory

router = APIRouter(prefix="/api/v1", tags=["integrations"])


def _load_contribution(db: Session, contribution_id: str) -> ContributionEvent:
    contribution = (
        db.query(ContributionEvent)
        .options(joinedload(ContributionEvent.participants))
        .filter(ContributionEvent.id == contribution_id)
        .first()
    )
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    return contribution


@router.get("/reviews/queue")
def human_review_queue(limit: int = 20, db: Session = Depends(get_db)):
    return {
        "compat": "meritocrab-review-queue-v0",
        "count": limit,
        "items": list_human_review_queue(db, limit=limit),
    }


@router.get("/contributions/{contribution_id}/attribution-proof")
def contribution_attribution_proof(contribution_id: str, db: Session = Depends(get_db)):
    contribution = _load_contribution(db, contribution_id)
    return build_attribution_merkle_proof(contribution.evidence)


@router.post("/contributions/{contribution_id}/attribution-proof/verify")
def verify_contribution_attribution_proof(
    contribution_id: str,
    body: dict,
    db: Session = Depends(get_db),
):
    contribution = _load_contribution(db, contribution_id)
    proof = build_attribution_merkle_proof(contribution.evidence)
    builder_slug = body.get("builder_slug")
    if not builder_slug:
        raise HTTPException(status_code=400, detail="builder_slug is required")
    return {
        "contribution_id": contribution_id,
        "builder_slug": builder_slug,
        "valid": verify_attribution_merkle_proof(proof, builder_slug),
        "merkle_root": proof.get("merkle_root"),
    }


@router.get("/contributions/{contribution_id}/experts")
def contribution_expert_cards(contribution_id: str, db: Session = Depends(get_db)):
    contribution = _load_contribution(db, contribution_id)
    return {
        "contribution_id": contribution_id,
        "compat": "proof-of-contribution-v0",
        "experts": expert_cards_from_contribution(db, contribution),
    }


@router.get("/contributions/{contribution_id}/reward-advisory")
def contribution_reward_advisory(contribution_id: str, db: Session = Depends(get_db)):
    contribution = _load_contribution(db, contribution_id)
    return build_reward_advisory(db, contribution)


@router.get("/contributions/{contribution_id}/evidence-check")
def contribution_evidence_check(contribution_id: str, db: Session = Depends(get_db)):
    contribution = _load_contribution(db, contribution_id)
    return validate_evidence_full(contribution.evidence)


@router.get("/contributions/{contribution_id}/code-attribution-context")
def contribution_code_attribution_context(contribution_id: str, db: Session = Depends(get_db)):
    contribution = _load_contribution(db, contribution_id)
    return build_code_attribution_context(contribution.evidence)


@router.get("/contributions/{contribution_id}/external-inspirations")
def contribution_external_inspirations(contribution_id: str, db: Session = Depends(get_db)):
    contribution = _load_contribution(db, contribution_id)
    result = get_inspirations_for_contribution(db, contribution.evidence)
    result["contribution_id"] = contribution_id
    return result


@router.get("/contributions/{contribution_id}/community-partners")
def contribution_community_partners(contribution_id: str, db: Session = Depends(get_db)):
    contribution = _load_contribution(db, contribution_id)
    return get_contribution_partner_context(db, contribution)


@router.get("/contributions/{contribution_id}/federation-context")
def contribution_federation_context(contribution_id: str, db: Session = Depends(get_db)):
    contribution = _load_contribution(db, contribution_id)
    return get_contribution_federation_context(db, contribution)


@router.get("/entities/{entity_id}/reputation/portable")
def entity_portable_reputation(entity_id: str, db: Session = Depends(get_db)):
    try:
        return build_portable_reputation_by_id(db, entity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/federation/reputation/{portable_id}/portable")
def portable_reputation_by_id(portable_id: str, db: Session = Depends(get_db)):
    try:
        return build_portable_reputation_by_portable_id(db, portable_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/entities/{entity_id}/reputation/audit")
def entity_reputation_audit(entity_id: str, limit: int = 50, db: Session = Depends(get_db)):
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return {
        "entity_id": entity_id,
        "compat": "meritocrab-audit-v0",
        "entries": list_reputation_audit(db, entity_id, limit=limit),
    }


@router.get("/invocations/{trace_id}/receipt")
def get_invocation_receipt(trace_id: str, db: Session = Depends(get_db)):
    trace = load_trace_for_receipt(db, trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Invocation trace not found")
    receipt = build_agent_receipt(trace)
    return receipt


@router.post("/invocations/{trace_id}/receipt/verify")
def verify_invocation_receipt(trace_id: str, db: Session = Depends(get_db)):
    trace = load_trace_for_receipt(db, trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Invocation trace not found")
    receipt = build_agent_receipt(trace)
    return {"trace_id": trace_id, "valid": verify_agent_receipt(receipt), "receipt_hash": receipt["integrity"]["receipt_hash"]}


@router.post("/agents/{agent_id}/feedback", response_model=AgentFeedbackOut)
def submit_agent_feedback(
    agent_id: str,
    body: AgentFeedbackIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    try:
        feedback = give_agent_feedback(
            db,
            agent_entity_id=agent_id,
            reviewer_entity_id=current_user.entity_id,
            score=body.score,
            comment=body.comment,
            contribution_id=body.contribution_id,
            tag1=body.tag1,
            tag2=body.tag2,
        )
        db.commit()
        db.refresh(feedback)
        return feedback
    except AgentReputationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/agents/{agent_id}/reputation/summary", response_model=AgentReputationSummary)
def agent_reputation_summary(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Entity).filter(Entity.id == agent_id).first()
    if not agent or agent.entity_type != EntityType.agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    try:
        return get_agent_reputation_summary(db, agent_id)
    except AgentReputationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/agents/{agent_id}/reputation/clients")
def agent_reputation_clients(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Entity).filter(Entity.id == agent_id).first()
    if not agent or agent.entity_type != EntityType.agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent_entity_id": agent_id, "clients": list_agent_clients(db, agent_id)}
