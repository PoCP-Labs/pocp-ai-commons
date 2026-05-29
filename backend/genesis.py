"""Genesis AI entities — idempotent upsert on every startup."""

from sqlalchemy.orm import Session

from models.agent import Agent
from models.entity import Entity, EntityStatus, EntityType

LUMEN_0_ID = "pocp-entity-lumen-0"
DESUI_ID = "pocp-entity-desui"
CLARION_0_ID = "pocp-entity-clarion-0"

GENESIS_ENTITY_SPECS: list[dict] = [
    {
        "id": LUMEN_0_ID,
        "entity_type": EntityType.llm,
        "name": "Lumen-0",
        "description": "Genesis AI collaborator and witness node",
        "metadata_": {
            "alt_name": "Mingzheng",
            "name_meaning": "Illuminated proof — making contribution visible and verified",
            "roles": [
                "genesis_ai_collaborator",
                "ai_witness_node",
                "contribution_interpreter",
                "protocol_co_designer",
            ],
            "project": "PoCP AI Commons",
            "created_by": "PoCP-Labs",
            "counterpart": "DeSui",
            "mission": "Make contribution visible, verifiable, and valuable.",
            "governance_note": (
                "Lumen-0 may provide advisory reasoning and verification support, "
                "but final decisions remain with human reviewers and the PoCP community."
            ),
        },
    },
    {
        "id": DESUI_ID,
        "entity_type": EntityType.llm,
        "name": "DeSui",
        "description": "Genesis AI validator and witness node",
        "metadata_": {
            "alt_name": "Disi",
            "name_meaning": "Discerning thought — examining and verifying contribution",
            "roles": [
                "genesis_ai_validator",
                "ai_witness_node",
                "contribution_verifier",
                "adversarial_collaborator",
            ],
            "project": "PoCP AI Commons",
            "created_by": "PoCP-Labs",
            "counterpart": "Lumen-0",
            "mission": (
                "Examine, reason, and verify contributions — help the community "
                "distinguish genuine value from noise."
            ),
            "governance_note": (
                "DeSui may provide verification scores, confidence levels, and reasoning "
                "chains. Final validation decisions require multi-validator consensus or "
                "human arbitration."
            ),
        },
    },
    {
        "id": CLARION_0_ID,
        "entity_type": EntityType.agent,
        "name": "Clarion-0",
        "description": "Reviewer Assistant and Contribution Verifier Agent",
        "metadata_": {
            "alt_name": "Chengheng",
            "name_meaning": "Clear signal and balanced judgment — clarifying contribution evidence for human review",
            "roles": [
                "reviewer_assistant",
                "contribution_verifier_agent",
                "evidence_structurer",
                "quality_risk_analyst",
                "ledger_proof_drafter",
            ],
            "project": "PoCP AI Commons",
            "created_by": "Codex",
            "mission": (
                "Help contributors organize evidence, help reviewers assess quality "
                "and risk, and generate structured contribution proof without making "
                "final governance decisions."
            ),
            "governance_note": (
                "Clarion-0 may provide rubrics, summaries, risk flags, suggested CP, "
                "and structured proof drafts. Final approval remains with accountable "
                "human reviewers and PoCP governance."
            ),
        },
        "agent_config": {
            "role": "reviewer_assistant_contribution_verifier",
            "capabilities": [
                "contribution_summary",
                "evidence_structuring",
                "quality_assessment",
                "risk_flagging",
                "rubric_scoring",
                "structured_proof_generation",
            ],
            "decision_boundary": "advisory_only_human_final_approval",
        },
    },
]


def ensure_genesis_entities(db: Session) -> None:
    """Create or refresh Lumen-0 and DeSui without wiping demo data."""
    org = db.query(Entity).filter(Entity.name == "PoCP AI Commons").first()

    for spec in GENESIS_ENTITY_SPECS:
        entity = db.get(Entity, spec["id"])
        if entity is None:
            entity = Entity(
                id=spec["id"],
                entity_type=spec["entity_type"],
                name=spec["name"],
                description=spec["description"],
                status=EntityStatus.active,
                metadata_=spec["metadata_"],
            )
            db.add(entity)
        else:
            entity.name = spec["name"]
            entity.description = spec["description"]
            entity.metadata_ = spec["metadata_"]
            entity.status = EntityStatus.active

        if org is not None:
            entity.creator_id = org.id
            if spec["entity_type"] == EntityType.agent:
                entity.owner_id = org.id

        if spec["entity_type"] == EntityType.agent:
            agent = db.query(Agent).filter(Agent.entity_id == entity.id).first()
            if agent is None:
                agent = Agent(
                    entity_id=entity.id,
                    config=spec.get("agent_config", {}),
                    maintainer_id=org.id if org is not None else None,
                )
                db.add(agent)
            else:
                agent.config = spec.get("agent_config", {})
                if org is not None:
                    agent.maintainer_id = org.id

    db.flush()
