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
from models.task import Task, TaskStatus
from models.wallet import ReputationScore, Wallet
from schemas import (
    AgentOut,
    AiVerifyIn,
    ApproveIn,
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
from services.contribution import approve_contribution, grant_registration_credits, run_ai_verification
from services.graph import build_contribution_graph
from services.invocation import record_invocation
from services.rejection import reject_contribution

router = APIRouter(prefix="/api/v1", tags=["pocp"])


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


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.created_at.desc()).all()


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


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


@router.get("/wallets/{entity_id}", response_model=WalletOut)
def get_wallet(entity_id: str, db: Session = Depends(get_db)):
    wallet = db.query(Wallet).filter(Wallet.entity_id == entity_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found for entity")
    return wallet


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
def create_task(body: TaskCreate, db: Session = Depends(get_db)):
    task = Task(
        title=body.title,
        description=body.description,
        sponsor_id=body.sponsor_id,
        status=TaskStatus.open,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.post("/contributions", response_model=ContributionOut, status_code=201)
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
def verify_contribution(
    contribution_id: str,
    body: AiVerifyIn,
    db: Session = Depends(get_db),
):
    contribution = db.query(ContributionEvent).filter(ContributionEvent.id == contribution_id).first()
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    if contribution.status not in (ContributionStatus.submitted, ContributionStatus.draft):
        raise HTTPException(status_code=400, detail=f"Cannot verify contribution in status: {contribution.status.value}")

    run_ai_verification(
        db,
        contribution,
        model_provider=body.model_provider,
        score=body.score,
        feedback=body.feedback,
    )
    db.commit()
    return get_contribution(contribution_id, db)


@router.post("/contributions/{contribution_id}/approve", response_model=ContributionOut)
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
    return get_contribution(contribution_id, db)


@router.post("/contributions/{contribution_id}/reject", response_model=ContributionOut)
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

@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, db: Session = Depends(get_db)):
    """Send a message to the AI. Consumes AI Credits from the entity's wallet.

    Uses the configured AI provider (DeepSeek, OpenAI, Ollama, etc.) via
    environment variables AI_API_KEY, AI_API_BASE, AI_MODEL.
    Falls back to simulation if no API key is configured.
    """
    from services.ai import AiModelClient, get_ai_client
    from services.contribution import spend_ai_credits

    entity = db.query(Entity).filter(Entity.id == body.entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Calculate cost based on message complexity
    msg_len = len(body.message)
    cost = max(1.0, round(msg_len / 500, 2))
    cost = min(cost, 50.0)  # Cap at 50 credits per message

    # Spend credits
    try:
        spend_result = spend_ai_credits(
            db,
            entity_id=body.entity_id,
            amount=cost,
            reason=f"AI chat: {body.message[:60]}",
        )
    except ValueError as e:
        raise HTTPException(status_code=402, detail=str(e))

    # Call AI model
    client = AiModelClient(
        api_base="",
        api_key="",
        model=body.model_provider,
    )
    try:
        result = await get_ai_client().chat(
            message=body.message,
            system_prompt=(
                "You are the PoCP AI Commons assistant. "
                "You help users understand Proof of Contribution Protocol (PoCP), "
                "guide them through contribution tasks, explain AI Credits, "
                "and assist with learning and research using the platform. "
                "Be helpful, clear, and encouraging. "
                "When asked about your identity, say you are pocp-helper."
            ),
        )
        reply = result["reply"]
    except Exception as e:
        reply = (
            f"[{body.model_provider}] "
            f"AI service unavailable at the moment. "
            f"Please check backend logs or configure AI_API_KEY.\n\n"
            f"Error: {str(e)[:200]}\n\n"
            f"📊 Credits spent: {cost} | Remaining: {spend_result['remaining']}"
        )

    return ChatResponse(
        reply=reply,
        credits_used=cost,
        credits_remaining=spend_result["remaining"],
        transaction_id=spend_result["transaction_id"],
    )


@router.get("/chat/history", response_model=list[dict])
def list_chat_history(entity_id: str = "", limit: int = 20, db: Session = Depends(get_db)):
    """List recent credit transactions as chat history."""
    from models.wallet import CreditTransaction

    query = db.query(CreditTransaction).join(
        Wallet, CreditTransaction.wallet_id == Wallet.id
    )

    if entity_id:
        query = query.filter(Wallet.entity_id == entity_id)

    transactions = (
        query
        .filter(CreditTransaction.credit_type == CreditType.ai_credits)
        .order_by(CreditTransaction.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": t.id,
            "amount": t.amount,
            "reason": t.reason,
            "created_at": t.created_at.isoformat(),
        }
        for t in transactions
    ]
