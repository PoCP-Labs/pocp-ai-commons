import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.contribution import (
    ContributionEvent,
    ContributionParticipant,
    ContributionStatus,
    ParticipantRole,
)
from models.entity import Entity, EntityStatus, EntityType
from models.ledger import LedgerRecord
from models.organization import Organization
from models.task import Task, TaskStatus
from models.user_account import UserAccount
from models.wallet import ReputationScore, Wallet
from routers.auth import require_current_user
from schemas import (
    AgentOut,
    AgentCreate,
    AiVerifyIn,
    ApproveIn,
    RejectIn,
    ContributionCreate,
    ContributionGraph,
    ContributionOut,
    EntityCreate,
    EntityOut,
    InvocationCreate,
    InvocationOut,
    LedgerOut,
    OrganizationCreate,
    OrganizationOut,
    ReputationOut,
    SkillCreate,
    SkillOut,
    TaskCreate,
    TaskOut,
    WalletOut,
)
from services.anti_abuse import check_daily_contribution_limit, require_evidence
from services.ai_verify_service import ai_verify_service
from services.contribution import approve_contribution, grant_registration_credits, reject_contribution, run_ai_verification
from services.evidence import POCP_META_KEY, enrich_evidence
from services.graph import build_contribution_graph
from services.invocation import record_invocation
from services.evidence_validate import validate_evidence_urls
from services.org_foundation import can_sponsor_as_organization
from services.provenance import attach_provenance_to_evidence

router = APIRouter(prefix="/api/v1", tags=["pocp"])


def _assert_task_sponsor_allowed(db: Session, sponsor_id: str | None, current_user: UserAccount) -> None:
    if sponsor_id is None or sponsor_id == current_user.entity_id:
        return

    sponsor = db.query(Entity).filter(Entity.id == sponsor_id).first()
    if sponsor and sponsor.entity_type == EntityType.organization:
        if current_user.entity_id and can_sponsor_as_organization(
            db, sponsor_id, current_user.entity_id
        ):
            return

    raise HTTPException(status_code=403, detail="You cannot create tasks for this sponsor")


@router.get("/entities", response_model=list[EntityOut])
def list_entities(db: Session = Depends(get_db)):
    return db.query(Entity).order_by(Entity.created_at).all()


@router.get("/entities/{entity_id}", response_model=EntityOut)
def get_entity(entity_id: str, db: Session = Depends(get_db)):
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.get("/skills", response_model=list[SkillOut])
def list_skills(db: Session = Depends(get_db)):
    from models.skill import Skill

    return db.query(Skill).all()


@router.get("/agents", response_model=list[AgentOut])
def list_agents(db: Session = Depends(get_db)):
    from models.agent import Agent

    return db.query(Agent).all()


@router.post("/agents", response_model=AgentOut, status_code=201)
def create_agent(
    body: AgentCreate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    from models.agent import Agent

    maintainer = db.query(Entity).filter(Entity.id == body.maintainer_id).first()
    if not maintainer:
        raise HTTPException(status_code=404, detail="Maintainer entity not found")
    if body.maintainer_id != current_user.entity_id:
        raise HTTPException(status_code=403, detail="maintainer_id must match the authenticated entity")

    metadata = {
        "registry_compat": "erc-8004-offchain-v0",
        "service_endpoints": body.service_endpoints,
        "capabilities": body.capabilities,
        "registered_by": current_user.entity_id,
    }
    entity = Entity(
        entity_type=EntityType.agent,
        name=body.name,
        description=body.description,
        owner_id=body.maintainer_id,
        creator_id=body.maintainer_id,
        status=EntityStatus.active,
        metadata_=metadata,
    )
    db.add(entity)
    db.flush()

    agent = Agent(
        entity_id=entity.id,
        config={
            "capabilities": body.capabilities,
            "service_endpoints": body.service_endpoints,
        },
        maintainer_id=body.maintainer_id,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.created_at.desc()).all()


@router.get("/contributions", response_model=list[ContributionOut])
def list_contributions(db: Session = Depends(get_db)):
    return (
        db.query(ContributionEvent)
        .options(
            joinedload(ContributionEvent.participants),
            joinedload(ContributionEvent.ai_verifications),
            joinedload(ContributionEvent.human_reviews),
        )
        .order_by(ContributionEvent.created_at.desc())
        .all()
    )


@router.get("/contributions/{contribution_id}", response_model=ContributionOut)
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


@router.get("/wallets", response_model=list[WalletOut])
def list_wallets(db: Session = Depends(get_db)):
    return db.query(Wallet).all()


@router.get("/reputation", response_model=list[ReputationOut])
def list_reputation(db: Session = Depends(get_db)):
    return db.query(ReputationScore).order_by(ReputationScore.score.desc()).all()


@router.get("/ledger", response_model=list[LedgerOut])
def list_ledger(db: Session = Depends(get_db)):
    return db.query(LedgerRecord).order_by(LedgerRecord.created_at.desc()).all()


@router.get("/graph", response_model=ContributionGraph)
def get_contribution_graph(db: Session = Depends(get_db)):
    return build_contribution_graph(db)


@router.post("/entities", response_model=EntityOut, status_code=201)
def create_entity(body: EntityCreate, db: Session = Depends(get_db)):
    try:
        entity_type = EntityType(body.entity_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid entity_type: {body.entity_type}") from exc

    entity = Entity(
        entity_type=entity_type,
        name=body.name,
        description=body.description,
        owner_id=body.owner_id,
        creator_id=body.creator_id,
        status=EntityStatus.active,
    )
    db.add(entity)
    db.flush()
    grant_registration_credits(db, entity)
    db.commit()
    db.refresh(entity)
    return entity


@router.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(
    body: TaskCreate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    _assert_task_sponsor_allowed(db, body.sponsor_id, current_user)
    task = Task(
        title=body.title,
        description=body.description,
        sponsor_id=body.sponsor_id or current_user.entity_id,
        status=TaskStatus.open,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.post("/contributions", response_model=ContributionOut, status_code=201)
def submit_contribution(
    body: ContributionCreate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    task = db.query(Task).filter(Task.id == body.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if body.primary_entity_id != current_user.entity_id:
        raise HTTPException(status_code=403, detail="primary_entity_id must match the authenticated entity")

    require_evidence(body.evidence)
    check_daily_contribution_limit(db, current_user.entity_id)

    evidence = enrich_evidence(body.evidence)
    if body.provenance is not None:
        evidence = attach_provenance_to_evidence(
            evidence,
            declared_by_entity_id=current_user.entity_id,
            creation_mode=body.provenance.creation_mode,  # type: ignore[arg-type]
            ai_tools_used=body.provenance.ai_tools_used,
            human_experts_cited=body.provenance.human_experts_cited,
            review_depth=body.provenance.review_depth,
            notes=body.provenance.notes,
        )

    if os.getenv("POCP_VALIDATE_EVIDENCE_URLS", "false").lower() == "true":
        url_report = validate_evidence_urls(evidence)
        meta = dict(evidence.get(POCP_META_KEY) or {})
        meta["url_checks"] = url_report
        evidence[POCP_META_KEY] = meta

    contribution = ContributionEvent(
        task_id=body.task_id,
        primary_entity_id=current_user.entity_id,
        contribution_type=body.contribution_type,
        description=body.description,
        evidence=evidence,
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


@router.post("/contributions/{contribution_id}/verify", response_model=ContributionOut)
async def verify_contribution(
    contribution_id: str,
    body: AiVerifyIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    if os.getenv("ENABLE_MANUAL_VERIFY", "false").lower() != "true":
        raise HTTPException(
            status_code=403,
            detail="Manual verify is disabled; use /api/v1/contributions/{id}/auto-verify",
        )

    contribution = (
        db.query(ContributionEvent)
        .options(joinedload(ContributionEvent.task), joinedload(ContributionEvent.participants))
        .filter(ContributionEvent.id == contribution_id)
        .first()
    )
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    if contribution.primary_entity_id != current_user.entity_id:
        raise HTTPException(status_code=403, detail="Only the contribution owner can request manual verification")
    if contribution.status in (ContributionStatus.approved, ContributionStatus.rejected):
        raise HTTPException(status_code=400, detail=f"Cannot verify contribution in status: {contribution.status.value}")
    if contribution.status == ContributionStatus.ai_verified:
        raise HTTPException(
            status_code=400,
            detail="Contribution already passed AI verification; proceed to human approval",
        )

    if body.score > 0:
        run_ai_verification(
            db,
            contribution,
            model_provider=body.model_provider,
            score=body.score,
            feedback=body.feedback,
            required_passing_count=body.required_passing_count,
        )
    else:
        task = contribution.task
        rubric = await ai_verify_service(
            task_title=getattr(task, "title", None),
            task_description=getattr(task, "description", None),
            contribution_description=contribution.description,
            evidence=contribution.evidence,
            participants=[
                {
                    "entity_id": p.entity_id,
                    "role": p.role.value,
                    "weight": p.weight,
                    "evidence": p.evidence,
                }
                for p in contribution.participants
            ],
            provider=body.model_provider,
        )
        run_ai_verification(
            db,
            contribution,
            model_provider=rubric.provider,
            score=rubric.score,
            feedback=rubric.feedback,
            required_passing_count=body.required_passing_count,
            details=rubric.model_dump(),
        )
    db.commit()
    return get_contribution(contribution_id, db)


@router.post("/contributions/{contribution_id}/approve", response_model=ContributionOut)
def approve_contribution_endpoint(
    contribution_id: str,
    body: ApproveIn,
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
    if contribution.status != ContributionStatus.ai_verified:
        raise HTTPException(
            status_code=400,
            detail="Contribution must pass AI verification before human approval",
        )
    if body.reviewer_id != current_user.entity_id:
        raise HTTPException(status_code=403, detail="reviewer_id must match the authenticated entity")

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
    return get_contribution(contribution_id, db)


@router.post("/contributions/{contribution_id}/reject", response_model=ContributionOut)
def reject_contribution_endpoint(
    contribution_id: str,
    body: RejectIn,
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
    if contribution.status not in (ContributionStatus.submitted, ContributionStatus.ai_verified):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject contribution in status: {contribution.status.value}",
        )
    if body.reviewer_id != current_user.entity_id:
        raise HTTPException(status_code=403, detail="reviewer_id must match the authenticated entity")

    reviewer = db.query(Entity).filter(Entity.id == body.reviewer_id).first()
    if not reviewer or reviewer.entity_type != EntityType.human:
        raise HTTPException(status_code=400, detail="Reviewer must be a human entity")

    try:
        reject_contribution(db, contribution, body.reviewer_id, body.feedback)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return get_contribution(contribution_id, db)


@router.get("/invocations", response_model=list[InvocationOut])
def list_invocations(db: Session = Depends(get_db)):
    from models.invocation import InvocationTrace

    return (
        db.query(InvocationTrace)
        .options(joinedload(InvocationTrace.steps))
        .order_by(InvocationTrace.created_at.desc())
        .all()
    )


@router.post("/invocations", response_model=InvocationOut, status_code=201)
def create_invocation(body: InvocationCreate, db: Session = Depends(get_db)):
    from models.invocation import InvocationTrace

    try:
        trace = record_invocation(
            db,
            initiator_id=body.initiator_id,
            skill_entity_id=body.skill_entity_id,
            agent_entity_id=body.agent_entity_id,
            model_provider=body.model_provider,
            task_id=body.task_id,
            contribution_id=body.contribution_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return (
        db.query(InvocationTrace)
        .options(joinedload(InvocationTrace.steps))
        .filter(InvocationTrace.id == trace.id)
        .first()
    )


@router.post("/organizations", response_model=OrganizationOut, status_code=201)
def create_organization(body: OrganizationCreate, db: Session = Depends(get_db)):
    from models.organization import Organization

    proxy = db.query(Entity).filter(Entity.id == body.governance_proxy_id).first()
    if not proxy or proxy.entity_type != EntityType.human:
        raise HTTPException(status_code=400, detail="governance_proxy_id must be a human entity")

    entity = Entity(
        entity_type=EntityType.organization,
        name=body.name,
        description=body.description,
        owner_id=body.governance_proxy_id,
        creator_id=body.creator_id or body.governance_proxy_id,
        status=EntityStatus.active,
    )
    db.add(entity)
    db.flush()

    org = Organization(
        entity_id=entity.id,
        org_type=body.org_type,
        governance_proxy_id=body.governance_proxy_id,
        config={"governance": "human_proxy"},
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.get("/organizations", response_model=list[OrganizationOut])
def list_organizations(db: Session = Depends(get_db)):
    from models.organization import Organization

    return db.query(Organization).all()


@router.post("/skills", response_model=SkillOut, status_code=201)
def create_skill(body: SkillCreate, db: Session = Depends(get_db)):
    from models.skill import Skill

    maintainer = db.query(Entity).filter(Entity.id == body.maintainer_id).first()
    if not maintainer:
        raise HTTPException(status_code=404, detail="Maintainer entity not found")

    entity = Entity(
        entity_type=EntityType.skill,
        name=body.name,
        description=body.description,
        owner_id=body.maintainer_id,
        creator_id=body.maintainer_id,
        status=EntityStatus.active,
    )
    db.add(entity)
    db.flush()

    skill = Skill(
        entity_id=entity.id,
        version=body.version,
        prompt_template=body.prompt_template,
        maintainer_id=body.maintainer_id,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill
