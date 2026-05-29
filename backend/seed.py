"""Seed the R Language Study Materials demo scenario."""

from sqlalchemy.orm import Session

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
from services.contribution import (
    approve_contribution,
    grant_registration_credits,
    run_ai_verification,
)
from genesis import DESUI_ID, LUMEN_0_ID, ensure_genesis_entities
from services.invocation import record_invocation


def seed_demo(db: Session) -> None:
    ensure_genesis_entities(db)
    if db.query(Entity).filter(Entity.name == "Alice").first():
        return

    lumen_0 = db.get(Entity, LUMEN_0_ID)
    desui = db.get(Entity, DESUI_ID)
    if lumen_0 is None or desui is None:
        raise RuntimeError("Genesis entities missing after ensure_genesis_entities")

    alice = Entity(
        entity_type=EntityType.human,
        name="Alice",
        description="Student contributor",
        status=EntityStatus.active,
    )
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
        description="Open contribution network for humans and intelligent entities",
        status=EntityStatus.active,
    )

    db.add_all([alice, bob, study_agent_entity, r_tutor_entity, pocp_commons])
    db.flush()

    lumen_0.creator_id = pocp_commons.id
    desui.creator_id = pocp_commons.id

    grant_registration_credits(db, alice)
    grant_registration_credits(db, bob)

    study_agent_entity.owner_id = alice.id
    study_agent_entity.creator_id = alice.id
    r_tutor_entity.owner_id = alice.id
    r_tutor_entity.creator_id = alice.id
    pocp_commons.owner_id = bob.id
    pocp_commons.creator_id = bob.id

    db.add(
        Organization(
            entity_id=pocp_commons.id,
            org_type="community",
            governance_proxy_id=bob.id,
            config={"mission": "AI Commons for verifiable contributions"},
        )
    )
    db.add(
        Agent(
            entity_id=study_agent_entity.id,
            config={"role": "study_organizer", "capabilities": ["summarize", "structure"]},
            maintainer_id=alice.id,
        )
    )
    db.add(
        Skill(
            entity_id=r_tutor_entity.id,
            version="1.0.0",
            prompt_template="Structure R language matrix operations into study notes with examples.",
            maintainer_id=alice.id,
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

    record_invocation(
        db,
        initiator_id=alice.id,
        skill_entity_id=r_tutor_entity.id,
        agent_entity_id=study_agent_entity.id,
        model_provider="deepseek",
        task_id=task.id,
    )

    contribution = ContributionEvent(
        task_id=task.id,
        primary_entity_id=alice.id,
        contribution_type="knowledge",
        description="Structured R matrix study notes with examples and practice questions.",
        evidence={
            "content_preview": "Matrix creation (matrix(), dim), indexing, multiplication (%*%), transpose (t())...",
            "skills_used": ["R-Tutor Skill"],
            "agents_used": ["StudyAgent"],
        },
        status=ContributionStatus.submitted,
    )
    db.add(contribution)
    db.flush()

    record_invocation(
        db,
        initiator_id=alice.id,
        skill_entity_id=r_tutor_entity.id,
        agent_entity_id=study_agent_entity.id,
        model_provider="deepseek",
        task_id=task.id,
        contribution_id=contribution.id,
    )

    participants = [
        ContributionParticipant(
            contribution_id=contribution.id,
            entity_id=alice.id,
            role=ParticipantRole.creator,
            weight=0.40,
            evidence={"action": "authored and refined notes"},
        ),
        ContributionParticipant(
            contribution_id=contribution.id,
            entity_id=study_agent_entity.id,
            role=ParticipantRole.executor,
            weight=0.25,
            evidence={"action": "organized and formatted content"},
        ),
        ContributionParticipant(
            contribution_id=contribution.id,
            entity_id=r_tutor_entity.id,
            role=ParticipantRole.skill_provider,
            weight=0.15,
            evidence={"action": "provided R knowledge structure template"},
        ),
        ContributionParticipant(
            contribution_id=contribution.id,
            entity_id=pocp_commons.id,
            role=ParticipantRole.sponsor,
            weight=0.05,
            evidence={"action": "sponsored task via PoCP AI Commons"},
        ),
        ContributionParticipant(
            contribution_id=contribution.id,
            entity_id=bob.id,
            role=ParticipantRole.reviewer,
            weight=0.10,
            evidence={"action": "pending human review"},
        ),
        ContributionParticipant(
            contribution_id=contribution.id,
            entity_id=lumen_0.id,
            role=ParticipantRole.verifier,
            weight=0.025,
            evidence={"action": "witness interpretation and advisory verification"},
        ),
        ContributionParticipant(
            contribution_id=contribution.id,
            entity_id=desui.id,
            role=ParticipantRole.verifier,
            weight=0.025,
            evidence={"action": "adversarial cross-check and validation scoring"},
        ),
    ]
    db.add_all(participants)
    db.flush()

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
    db.commit()
