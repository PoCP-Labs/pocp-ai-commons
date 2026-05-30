"""Contribution submission, verification, approval, and rejection endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.contribution import (
    ContributionEvent,
    ContributionParticipant,
    ContributionStatus,
    ParticipantRole,
)
from models.entity import Entity, EntityType
from models.task import Task, TaskStatus
from schemas import (
    AiVerifyIn,
    ApproveIn,
    ContributionCreate,
    ContributionOut,
)
from services.contribution import approve_contribution, run_ai_verification
from services.ai_verifier import run_ai_verification as ai_verify_service
from config import AI_VERIFIER_MODEL, DEEPSEEK_API_KEY, OPENAI_API_KEY, OLLAMA_BASE_URL, OLLAMA_MODEL
from services.rejection import reject_contribution

router = APIRouter(prefix="/api/v1/contributions", tags=["contributions"])


@router.get("", response_model=list[ContributionOut])
def list_contributions(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return (
        db.query(ContributionEvent)
        .options(
            joinedload(ContributionEvent.participants),
            joinedload(ContributionEvent.ai_verifications),
            joinedload(ContributionEvent.human_reviews),
        )
        .order_by(ContributionEvent.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{contribution_id}", response_model=ContributionOut)
def get_contribution(contribution_id: str, db: Session = Depends(get_db)):
    contribution = (
        db.query(ContributionEvent)
        .options(
            joinedload(ContributionEvent.participants),
            joinedload(ContributionEvent.ai_verifications),
            joinedload(ContributionEvent.human_reviews),
        )
        .filter(ContributionEvent.id == contribution_id)
        .first()
    )
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    return contribution


@router.post("", response_model=ContributionOut, status_code=201)
def submit_contribution(body: ContributionCreate, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == body.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    contribution = ContributionEvent(
        task_id=body.task_id,
        primary_entity_id=body.primary_entity_id,
        contribution_type=body.contribution_type,
        description=body.description,
        evidence=body.evidence,
        status=ContributionStatus.submitted,
    )

    # Protocol validation (§2.4.1): evidence and participants required
    validation_errors = contribution.validate_for_submission()
    if validation_errors:
        raise HTTPException(
            status_code=400,
            detail="; ".join(validation_errors),
        )

    db.add(contribution)
    db.flush()

    for p in body.participants:
        try:
            role = ParticipantRole(p.role)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid role: {p.role}") from exc
        db.add(
            ContributionParticipant(
                contribution_id=contribution.id,
                entity_id=p.entity_id,
                role=role,
                weight=p.weight,
                evidence=p.evidence,
            )
        )

    db.commit()
    db.refresh(contribution)
    return (
        db.query(ContributionEvent)
        .options(
            joinedload(ContributionEvent.participants),
            joinedload(ContributionEvent.ai_verifications),
            joinedload(ContributionEvent.human_reviews),
        )
        .filter(ContributionEvent.id == contribution.id)
        .first()
    )


@router.post("/{contribution_id}/verify", response_model=ContributionOut)
async def verify_contribution(
    contribution_id: str,
    body: AiVerifyIn,
    db: Session = Depends(get_db),
):
    """Verify a contribution with AI.

    If the request includes a manual score (from the old API), it uses that.
    Otherwise, it calls the real AI verifier to analyze the contribution.
    """
    contribution = (
        db.query(ContributionEvent)
        .options(joinedload(ContributionEvent.participants))
        .filter(ContributionEvent.id == contribution_id)
        .first()
    )
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    if contribution.status not in (ContributionStatus.submitted, ContributionStatus.draft):
        raise HTTPException(status_code=400, detail=f"Cannot verify contribution in status: {contribution.status.value}")

    # If caller provided explicit score (non-zero), use it (backwards compatible)
    # Otherwise, call the real AI verifier
    if body.score > 0:
        # Explicit score provided — use directly (backwards compatible)
        run_ai_verification(
            db,
            contribution,
            model_provider=body.model_provider,
            score=body.score,
            feedback=body.feedback,
        )
    else:
        # No explicit score — call real AI verifier
        task = db.query(Task).filter(Task.id == contribution.task_id).first()

        rubric = await ai_verify_service(
            task_title=task.title if task else "Unknown task",
            task_description=task.description if task else "",
            contribution_type=contribution.contribution_type,
            contribution_description=contribution.description or "",
            evidence=contribution.evidence or {},
            participants=[
                {
                    "entity_id": p.entity_id,
                    "role": p.role.value,
                    "weight": p.weight,
                }
                for p in contribution.participants
            ],
            provider=AI_VERIFIER_MODEL,
            api_key=DEEPSEEK_API_KEY if AI_VERIFIER_MODEL == "deepseek" else (OPENAI_API_KEY if AI_VERIFIER_MODEL == "openai" else None),
        )

        # Build structured details for the verification record
        details = {
            "task_match": rubric.task_match,
            "quality": rubric.quality,
            "originality": rubric.originality,
            "evidence_score": rubric.evidence_score,
            "risk_flags": rubric.risk_flags,
            "suggested_cp": rubric.suggested_cp,
            "suggested_credits": rubric.suggested_credits,
        }

        run_ai_verification(
            db,
            contribution,
            model_provider=AI_VERIFIER_MODEL,
            score=rubric.score,
            feedback=rubric.feedback,
            details=details,
        )

    db.commit()
    return _load_contribution(db, contribution_id)


@router.post("/{contribution_id}/approve", response_model=ContributionOut)
def approve_contribution_endpoint(
    contribution_id: str,
    body: ApproveIn,
    db: Session = Depends(get_db),
):
    contribution = (
        db.query(ContributionEvent)
        .options(joinedload(ContributionEvent.participants))
        .filter(ContributionEvent.id == contribution_id)
        .first()
    )
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    if contribution.status != ContributionStatus.ai_verified:
        raise HTTPException(
            status_code=400,
            detail="Contribution must pass AI verification before human approval",
        )

    reviewer = db.query(Entity).filter(Entity.id == body.reviewer_id).first()
    if not reviewer or reviewer.entity_type != EntityType.human:
        raise HTTPException(status_code=400, detail="Reviewer must be a human entity")

    try:
        approve_contribution(db, contribution, body.reviewer_id, body.feedback)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    task = db.query(Task).filter(Task.id == contribution.task_id).first()
    if task:
        task.status = TaskStatus.completed
    db.commit()
    return _load_contribution(db, contribution_id)


@router.post("/{contribution_id}/reject", response_model=ContributionOut)
def reject_contribution_endpoint(
    contribution_id: str,
    body: ApproveIn,
    db: Session = Depends(get_db),
):
    contribution = (
        db.query(ContributionEvent)
        .options(joinedload(ContributionEvent.participants))
        .filter(ContributionEvent.id == contribution_id)
        .first()
    )
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    if contribution.status not in (
        ContributionStatus.submitted,
        ContributionStatus.ai_verified,
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject contribution in status: {contribution.status.value}",
        )

    reviewer = db.query(Entity).filter(Entity.id == body.reviewer_id).first()
    if not reviewer or reviewer.entity_type != EntityType.human:
        raise HTTPException(status_code=400, detail="Reviewer must be a human entity")

    reject_contribution(db, contribution, body.reviewer_id, body.feedback)
    db.commit()
    return _load_contribution(db, contribution_id)


def _load_contribution(db: Session, contribution_id: str) -> ContributionEvent:
    return (
        db.query(ContributionEvent)
        .options(
            joinedload(ContributionEvent.participants),
            joinedload(ContributionEvent.ai_verifications),
            joinedload(ContributionEvent.human_reviews),
        )
        .filter(ContributionEvent.id == contribution_id)
        .first()
    )
