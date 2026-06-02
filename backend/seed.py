"""Seed the R Language Study Materials demo scenario."""

from sqlalchemy.orm import Session

from genesis import DESUI_ID, LUMEN_0_ID, RAIN_ID, ensure_genesis_entities
from models.agent import Agent
from models.contribution import (
    ContributionEvent,
    ContributionParticipant,
    ContributionStatus,
    ParticipantRole,
)
from models.entity import Entity, EntityStatus, EntityType
from models.organization import Organization
from models.skill import Skill
from models.task import Task, TaskStatus
from services.auth import bind_user_account_to_entity
from services.contribution import (
    approve_contribution,
    grant_registration_credits,
    run_ai_verification,
)
from services.entity_dedup import merge_rain_duplicates
from services.entity_register import register_dataset, register_entity, register_tool
from services.compute_seed import ensure_demo_compute_profiles
from services.invocation import record_invocation
from services.entity_catalog import ensure_platform_entity_catalog
from services.org_foundation import ensure_pocp_org_foundation

R_DOCS_TOOL_ID = "pocp-entity-r-docs-tool"
R_MATRIX_DATASET_ID = "pocp-entity-r-matrix-dataset"
PENDING_DEMO_SKILL_ID = "pocp-entity-pending-demo-skill"


def ensure_pending_governance_demo(db: Session, pocp_commons: Entity, rain: Entity) -> None:
    """Skill owned by the org, pending until governance proxy (Bob) approves."""
    if db.get(Entity, PENDING_DEMO_SKILL_ID):
        return
    register_entity(
        db,
        entity_id=PENDING_DEMO_SKILL_ID,
        entity_type="skill",
        name="Community Review Demo Skill",
        description="Awaiting org governance proxy approval — visible in Account → Entity Review Queue",
        owner_id=pocp_commons.id,
        creator_id=rain.id,
        status=EntityStatus.pending,
        metadata={"demo": True, "review_queue": "governance_proxy"},
    )

def ensure_demo_ontology_entities(db: Session, rain: Entity) -> tuple[Entity, Entity]:
    """Idempotent Tool + Dataset exemplars for the extended pilot topology."""
    tool = db.get(Entity, R_DOCS_TOOL_ID)
    if tool is None:
        tool = register_tool(
            db,
            entity_id=R_DOCS_TOOL_ID,
            name="R Docs MCP Tool",
            description="MCP tool for R documentation lookup during study note authoring",
            maintainer_id=rain.id,
            tool_kind="mcp",
            mcp_server="r-docs",
            capabilities=["lookup", "cite"],
            service_endpoints={"docs": "https://cran.r-project.org/manuals.html"},
        )
    dataset = db.get(Entity, R_MATRIX_DATASET_ID)
    if dataset is None:
        dataset = register_dataset(
            db,
            entity_id=R_MATRIX_DATASET_ID,
            name="R Matrix Reference Dataset",
            description="Curated matrix operation examples and practice items for R study materials",
            maintainer_id=rain.id,
            source_uri="https://example.com/pocp/r-matrix-reference.json",
            license="CC-BY-4.0",
            data_format="json",
            content_hash="demo-r-matrix-v1",
        )
    return tool, dataset


def demo_contribution_evidence() -> dict:
    return {
        "content_preview": "Matrix creation (matrix(), dim), indexing, multiplication (%*%), transpose (t())...",
        "skills_used": ["R-Tutor Skill"],
        "agents_used": ["StudyAgent"],
        "tools_used": ["R Docs MCP Tool"],
        "datasets_used": ["R Matrix Reference Dataset"],
    }


def build_demo_participants(
    contribution_id: str,
    *,
    rain_id: str,
    study_agent_id: str,
    r_tutor_id: str,
    tool_id: str,
    dataset_id: str,
    sponsor_id: str,
    reviewer_id: str,
    lumen_id: str,
    desui_id: str,
) -> list[ContributionParticipant]:
    specs: list[tuple[str, ParticipantRole, float, dict]] = [
        (rain_id, ParticipantRole.creator, 0.35, {"action": "authored and refined notes"}),
        (study_agent_id, ParticipantRole.executor, 0.22, {"action": "organized and formatted content"}),
        (r_tutor_id, ParticipantRole.skill_provider, 0.13, {"action": "provided R knowledge structure template"}),
        (tool_id, ParticipantRole.tool_provider, 0.05, {"action": "R documentation lookup via MCP"}),
        (dataset_id, ParticipantRole.data_provider, 0.05, {"action": "matrix examples and practice items corpus"}),
        (sponsor_id, ParticipantRole.sponsor, 0.05, {"action": "sponsored task via PoCP AI Commons"}),
        (reviewer_id, ParticipantRole.reviewer, 0.10, {"action": "pending human review"}),
        (lumen_id, ParticipantRole.witness, 0.03, {"action": "witness interpretation and coherence check"}),
        (desui_id, ParticipantRole.verifier, 0.02, {"action": "adversarial cross-check and validation scoring"}),
    ]
    return [
        ContributionParticipant(
            contribution_id=contribution_id,
            entity_id=entity_id,
            role=role,
            weight=weight,
            evidence=evidence,
        )
        for entity_id, role, weight, evidence in specs
    ]


def _find_demo_contribution(db: Session) -> ContributionEvent | None:
    candidates = (
        db.query(ContributionEvent)
        .filter(
            ContributionEvent.primary_entity_id == RAIN_ID,
            ContributionEvent.description.contains("matrix"),
        )
        .order_by(ContributionEvent.created_at)
        .all()
    )
    if not candidates:
        return None
    # Upgrade the canonical seeded demo (richest participant graph), not ad-hoc matrix notes.
    return max(
        candidates,
        key=lambda c: db.query(ContributionParticipant)
        .filter(ContributionParticipant.contribution_id == c.id)
        .count(),
    )


def upgrade_demo_pilot_topology(db: Session) -> bool:
    """Idempotently align an existing demo contribution with the extended entity ontology."""
    rain = db.get(Entity, RAIN_ID)
    lumen_0 = db.get(Entity, LUMEN_0_ID)
    desui = db.get(Entity, DESUI_ID)
    if rain is None or lumen_0 is None or desui is None:
        return False

    contribution = _find_demo_contribution(db)
    if contribution is None:
        return False

    tool, dataset = ensure_demo_ontology_entities(db, rain)
    study_agent = db.query(Entity).filter(Entity.name == "StudyAgent").first()
    r_tutor = db.query(Entity).filter(Entity.name == "R-Tutor Skill").first()
    pocp_commons = db.query(Entity).filter(Entity.name == "PoCP AI Commons").first()
    bob = db.query(Entity).filter(Entity.name == "Bob").first()
    if not all([study_agent, r_tutor, pocp_commons, bob]):
        return False

    changed = False
    evidence = dict(contribution.evidence or {})
    for key, values in (
        ("tools_used", demo_contribution_evidence()["tools_used"]),
        ("datasets_used", demo_contribution_evidence()["datasets_used"]),
    ):
        merged = list(evidence.get(key) or [])
        for value in values:
            if value not in merged:
                merged.append(value)
                changed = True
        evidence[key] = merged
    if evidence != (contribution.evidence or {}):
        contribution.evidence = evidence
        changed = True

    participants = (
        db.query(ContributionParticipant)
        .filter(ContributionParticipant.contribution_id == contribution.id)
        .all()
    )
    has_witness = any(
        p.entity_id == LUMEN_0_ID and p.role == ParticipantRole.witness for p in participants
    )
    has_tool = any(p.entity_id == tool.id and p.role == ParticipantRole.tool_provider for p in participants)
    if has_witness and has_tool and len(participants) >= 9:
        return changed

    for participant in participants:
        db.delete(participant)
    db.flush()
    db.add_all(
        build_demo_participants(
            contribution.id,
            rain_id=rain.id,
            study_agent_id=study_agent.id,
            r_tutor_id=r_tutor.id,
            tool_id=tool.id,
            dataset_id=dataset.id,
            sponsor_id=pocp_commons.id,
            reviewer_id=bob.id,
            lumen_id=lumen_0.id,
            desui_id=desui.id,
        )
    )
    return True


def ensure_demo_accounts(db: Session, rain: Entity, bob: Entity) -> None:
    bind_user_account_to_entity(
        db,
        entity=rain,
        provider="dev",
        provider_user_id="rain@example.com",
        username="rain",
        email="rain@example.com",
    )
    bind_user_account_to_entity(
        db,
        entity=bob,
        provider="dev",
        provider_user_id="bob@example.com",
        username="bob",
        email="bob@example.com",
    )


def seed_demo(db: Session) -> None:
    ensure_genesis_entities(db)
    merge_rain_duplicates(db)
    ensure_pocp_org_foundation(db)
    existing_rain = db.get(Entity, RAIN_ID)
    existing_bob = db.query(Entity).filter(Entity.name == "Bob").first()
    has_demo_contribution = db.query(ContributionEvent).count() > 0
    # Skip full re-seed only when demo humans AND at least one contribution exist.
    if existing_rain and existing_bob and has_demo_contribution:
        tool, dataset = ensure_demo_ontology_entities(db, existing_rain)
        pocp_commons = db.query(Entity).filter(Entity.name == "PoCP AI Commons").first()
        lumen = db.get(Entity, LUMEN_0_ID)
        desui = db.get(Entity, DESUI_ID)
        ensure_demo_compute_profiles(
            db,
            rain=existing_rain,
            lumen=lumen,
            desui=desui,
            tool=tool,
            org=pocp_commons,
        )
        upgrade_demo_pilot_topology(db)
        ensure_platform_entity_catalog(db)
        ensure_demo_accounts(db, existing_rain, existing_bob)
        db.commit()
        return

    lumen_0 = db.get(Entity, LUMEN_0_ID)
    desui = db.get(Entity, DESUI_ID)
    if lumen_0 is None or desui is None:
        raise RuntimeError("Genesis entities missing after ensure_genesis_entities")

    rain = db.get(Entity, RAIN_ID)
    if rain is None:
        rain = Entity(
            id=RAIN_ID,
            entity_type=EntityType.human,
            name="Rain",
            description="Platform founder and contributor",
            status=EntityStatus.active,
        )
        db.add(rain)
    else:
        rain.description = "Platform founder and contributor"
        rain.status = EntityStatus.active
    bob = Entity(
        entity_type=EntityType.human,
        name="Bob",
        description="Human reviewer",
        status=EntityStatus.active,
    )
    study_agent_entity = Entity(
        entity_type=EntityType.agent,
        name="StudyAgent",
        description="Assistant for organizing study materials",
        status=EntityStatus.active,
    )
    r_tutor_entity = Entity(
        entity_type=EntityType.skill,
        name="R-Tutor Skill",
        description="R language knowledge structuring capability",
        status=EntityStatus.active,
    )
    pocp_commons = Entity(
        entity_type=EntityType.organization,
        name="PoCP AI Commons",
        description=(
            "Open contribution network founded and sponsored by Rain; "
            "governed by the Genesis manifesto (docs/genesis/)."
        ),
        status=EntityStatus.active,
    )

    db.add_all([bob, study_agent_entity, r_tutor_entity, pocp_commons])
    db.flush()

    lumen_0.creator_id = pocp_commons.id
    desui.creator_id = pocp_commons.id

    grant_registration_credits(db, rain)
    grant_registration_credits(db, bob)
    ensure_demo_accounts(db, rain, bob)

    r_docs_tool, r_matrix_dataset = ensure_demo_ontology_entities(db, rain)

    study_agent_entity.owner_id = rain.id
    study_agent_entity.creator_id = rain.id
    r_tutor_entity.owner_id = rain.id
    r_tutor_entity.creator_id = rain.id
    pocp_commons.owner_id = rain.id
    pocp_commons.creator_id = rain.id

    ensure_pending_governance_demo(db, pocp_commons, rain)

    db.add(
        Organization(
            entity_id=pocp_commons.id,
            org_type="community",
            governance_proxy_id=bob.id,
            config={
                "mission": "AI Commons for verifiable contributions",
                "founder_id": rain.id,
                "primary_sponsor_id": rain.id,
                "genesis_manifesto": [
                    "GENESIS.md",
                    "docs/genesis/README.md",
                    "docs/genesis/zh-CN.md",
                ],
                "platform_language": "en",
                "governance_note": (
                    "Rain founded the org and drafted the Genesis manifesto; "
                    "Bob is governance proxy for demo human review."
                ),
            },
        )
    )
    db.add(
        Agent(
            entity_id=study_agent_entity.id,
            config={"role": "study_organizer", "capabilities": ["summarize", "structure"]},
            maintainer_id=rain.id,
        )
    )
    db.add(
        Skill(
            entity_id=r_tutor_entity.id,
            version="1.0.0",
            prompt_template="Structure R language matrix operations into study notes with examples.",
            maintainer_id=rain.id,
        )
    )

    task = Task(
        title="Organize R Language Matrix Study Notes",
        description="Create structured study notes covering matrix operations in R for exam preparation.",
        sponsor_id=pocp_commons.id,
        status=TaskStatus.open,
    )
    db.add(task)
    db.flush()

    contribution = ContributionEvent(
        task_id=task.id,
        primary_entity_id=rain.id,
        contribution_type="knowledge",
        description="Structured R matrix study notes with examples and practice questions.",
        evidence=demo_contribution_evidence(),
        status=ContributionStatus.submitted,
    )
    db.add(contribution)
    db.flush()

    record_invocation(
        db,
        initiator_id=rain.id,
        skill_entity_id=r_tutor_entity.id,
        agent_entity_id=study_agent_entity.id,
        model_provider="deepseek",
        task_id=task.id,
        contribution_id=contribution.id,
    )

    db.add_all(
        build_demo_participants(
            contribution.id,
            rain_id=rain.id,
            study_agent_id=study_agent_entity.id,
            r_tutor_id=r_tutor_entity.id,
            tool_id=r_docs_tool.id,
            dataset_id=r_matrix_dataset.id,
            sponsor_id=pocp_commons.id,
            reviewer_id=bob.id,
            lumen_id=lumen_0.id,
            desui_id=desui.id,
        )
    )
    db.flush()

    ensure_demo_compute_profiles(
        db,
        rain=rain,
        lumen=lumen_0,
        desui=desui,
        tool=r_docs_tool,
        org=pocp_commons,
    )

    run_ai_verification(
        db,
        contribution,
        model_provider="Lumen-0",
        score=0.88,
        feedback="Notes cover key matrix concepts with accurate R syntax. Evidence is coherent and task-aligned.",
        required_passing_count=2,
    )
    run_ai_verification(
        db,
        contribution,
        model_provider="DeSui",
        score=0.85,
        feedback="Content quality meets threshold. Minor gaps in advanced indexing examples; recommend human review.",
        required_passing_count=2,
    )
    approve_contribution(
        db,
        contribution,
        reviewer_id=bob.id,
        feedback="Excellent structure. Approved for CP and AI Credits.",
    )

    task.status = TaskStatus.completed
    ensure_platform_entity_catalog(db)
    db.commit()
