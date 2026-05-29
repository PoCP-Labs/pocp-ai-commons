"""
PoCP AI Commons — Protected Route Examples
=============================================
Demonstrates how to apply auth dependencies to existing endpoints.

This module provides protected versions of key write operations that
require authentication. Read-only endpoints remain public.

Integration guide:
- Import `get_current_account` or `get_current_entity` from `deps`
- Add as a Depends() parameter to any route handler
- The route will automatically require a valid Bearer token
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from database import get_db
from deps import get_current_account, get_current_entity, require_superuser
from models.account import Account
from models.contribution import (
    ContributionEvent,
    ContributionParticipant,
    ContributionStatus,
    ParticipantRole,
)
from models.entity import Entity, EntityType
from models.task import Task, TaskStatus
from schemas import (
    ApproveIn,
    ContributionCreate,
    ContributionOut,
    TaskCreate,
    TaskOut,
)
from services.contribution import approve_contribution, run_ai_verification

router = APIRouter(prefix="/api/v1/protected", tags=["protected"])


# ---------------------------------------------------------------------------
# Protected Task Creation — only authenticated users can create tasks
# ---------------------------------------------------------------------------


@router.post("/tasks", response_model=TaskOut, status_code=201)
def create_task_authenticated(
    body: TaskCreate,
    account: Account = Depends(get_current_account),
    entity: Entity = Depends(get_current_entity),
    db: Session = Depends(get_db),
):
    """
    Create a task as the authenticated user.
    The sponsor_id is automatically set to the user's entity.
    """
    task = Task(
        title=body.title,
        description=body.description,
        sponsor_id=entity.id,  # Override with authenticated user's entity
        status=TaskStatus.open,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# ---------------------------------------------------------------------------
# Protected Contribution Submission — only authenticated users can submit
# ---------------------------------------------------------------------------


@router.post("/contributions", response_model=ContributionOut, status_code=201)
def submit_contribution_authenticated(
    body: ContributionCreate,
    account: Account = Depends(get_current_account),
    entity: Entity = Depends(get_current_entity),
    db: Session = Depends(get_db),
):
    """
    Submit a contribution as the authenticated user.
    The primary_entity_id is automatically set to the user's entity.
    """
    task = db.query(Task).filter(Task.id == body.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    contribution = ContributionEvent(
        task_id=body.task_id,
        primary_entity_id=entity.id,  # Override with authenticated user's entity
        contribution_type=body.contribution_type,
        description=body.description,
        evidence=body.evidence,
        status=ContributionStatus.submitted,
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


# ---------------------------------------------------------------------------
# Protected Approval — only superusers (human reviewers) can approve
# ---------------------------------------------------------------------------


@router.post(
    "/contributions/{contribution_id}/approve",
    response_model=ContributionOut,
)
def approve_contribution_authenticated(
    contribution_id: str,
    body: ApproveIn,
    account: Account = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    """
    Approve a contribution. Requires superuser (reviewer) privileges.
    The reviewer_id is automatically set to the authenticated user's entity.
    """
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

    try:
        approve_contribution(db, contribution, account.entity_id, body.feedback)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    task = db.query(Task).filter(Task.id == contribution.task_id).first()
    if task:
        task.status = TaskStatus.completed
    db.commit()

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
