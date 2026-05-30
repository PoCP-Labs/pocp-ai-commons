from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.entity import Entity, EntityType
from models.user_account import UserAccount
from routers.auth import require_current_user
from schemas import AgentFeedbackIn, AgentFeedbackOut, AgentReputationSummary
from services.agent_receipt import build_agent_receipt, load_trace_for_receipt, verify_agent_receipt
from services.agent_reputation import AgentReputationError, get_agent_reputation_summary, give_agent_feedback, list_agent_clients

router = APIRouter(prefix="/api/v1", tags=["integrations"])


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
