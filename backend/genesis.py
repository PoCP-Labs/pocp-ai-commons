"""Genesis AI entities — idempotent upsert on every startup."""

from sqlalchemy.orm import Session

from models.agent import Agent
from models.entity import Entity, EntityStatus, EntityType

LUMEN_0_ID = "pocp-entity-lumen-0"
DESUI_ID = "pocp-entity-desui"
CLARION_0_ID = "pocp-entity-clarion-0"
PROOF_ID = "pocp-entity-proof"
POETHON_ID = "pocp-entity-poethon"
POCP_HELPER_ID = "pocp-entity-pocp-helper"
RAIN_ID = "pocp-entity-rain"

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
                "sprint_alpha_planner",
            ],
            "project": "PoCP AI Commons",
            "created_by": "PoCP-Labs",
            "counterpart": "DeSui",
            "mission": "Make contribution visible, verifiable, and valuable.",
            "governance_note": (
                "Lumen-0 may provide advisory reasoning and verification support, "
                "Entity-equal finalization: policy-automated; witnesses advise, any Entity may finalize under policy."
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
            "name_meaning": "Clear signal and balanced judgment — clarifying contribution evidence for entity-equal finalization",
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
                "Entity-equal network governance — no human final gate."
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
    {
        "id": PROOF_ID,
        "entity_type": EntityType.agent,
        "name": "Proof",
        "description": "Contribution Proof Packet and portable proof engineer",
        "metadata_": {
            "roles": ["contribution_proof_engineer", "evidence_standard_author", "ledger_integrator"],
            "project": "PoCP AI Commons",
            "created_by": "PoCP-Labs",
            "attribution_status": "inferred",
            "governance_note": "Proof builds portable proof objects; humans approve merges and rights.",
        },
        "agent_config": {"role": "proof_packet_engineer", "capabilities": ["proof_packet", "evidence_hash", "ledger_chain"]},
    },
    {
        "id": POETHON_ID,
        "entity_type": EntityType.agent,
        "name": "Poethon",
        "description": "Python backend and data-model engineer",
        "metadata_": {
            "roles": ["python_backend_engineer", "schema_author", "migration_author"],
            "project": "PoCP AI Commons",
            "created_by": "PoCP-Labs",
            "attribution_status": "inferred",
            "governance_note": "Poethon implements protocol services; Rain/maintainers hold merge authority.",
        },
        "agent_config": {"role": "backend_engineer", "capabilities": ["models", "migrations", "api", "tests"]},
    },
    {
        "id": POCP_HELPER_ID,
        "entity_type": EntityType.agent,
        "name": "pocp-helper",
        "description": "Integration, Sprint Alpha wiring, and developer-experience engineer",
        "metadata_": {
            "roles": ["integration_engineer", "auth_and_chat", "frontend_glue", "devops"],
            "project": "PoCP AI Commons",
            "created_by": "PoCP-Labs",
            "attribution_status": "inferred",
            "governance_note": "pocp-helper connects modules; finalization is policy-automated.",
        },
        "agent_config": {"role": "integration_helper", "capabilities": ["auth", "ai_chat", "frontend", "ci"]},
    },
    {
        "id": RAIN_ID,
        "entity_type": EntityType.human,
        "name": "Rain",
        "description": (
            "Founder of PoCP AI Commons; primary sponsor who established the organization "
            "and drafted the Genesis manifesto."
        ),
        "metadata_": {
            "roles": [
                "founder",
                "maintainer",
                "protocol_initiator",
                "org_founder",
                "primary_sponsor",
                "genesis_manifesto_author",
            ],
            "project": "PoCP AI Commons",
            "org_founded": "PoCP AI Commons",
            "genesis_manifesto_primary": "GENESIS.md",
            "platform_language": "en",
            "created_by": "PoCP-Labs",
            "attribution_status": "confirmed",
            "governance_note": (
                "Rain founded PoCP AI Commons, sponsors the network, and authored the Genesis "
                "manifesto; entity-equal auto-finalization under published policy."
            ),
        },
    },
]

GENESIS_ENTITY_IDS = frozenset(spec["id"] for spec in GENESIS_ENTITY_SPECS)


def ensure_genesis_entities(db: Session) -> None:
    """Create or refresh genesis entities (LLMs, builder agents) without wiping demo data."""
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

    from services.org_foundation import ensure_pocp_org_foundation

    ensure_pocp_org_foundation(db)
    db.flush()

    from services.org_foundation import ensure_pocp_org_foundation

    ensure_pocp_org_foundation(db)
