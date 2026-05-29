"""Genesis LLM entities (Lumen-0, DeSui) — idempotent upsert on every startup."""

from sqlalchemy.orm import Session

from models.entity import Entity, EntityStatus, EntityType

LUMEN_0_ID = "pocp-entity-lumen-0"
DESUI_ID = "pocp-entity-desui"

GENESIS_ENTITY_SPECS: list[dict] = [
    {
        "id": LUMEN_0_ID,
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
]


def ensure_genesis_entities(db: Session) -> None:
    """Create or refresh Lumen-0 and DeSui without wiping demo data."""
    org = db.query(Entity).filter(Entity.name == "PoCP AI Commons").first()

    for spec in GENESIS_ENTITY_SPECS:
        entity = db.get(Entity, spec["id"])
        if entity is None:
            entity = Entity(
                id=spec["id"],
                entity_type=EntityType.llm,
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

    db.flush()
