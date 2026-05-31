"""PoCP AI Commons org foundation — Rain as founder, sponsor, and Genesis manifesto author."""

from sqlalchemy.orm import Session

from genesis import RAIN_ID
from models.entity import Entity, EntityType
from models.organization import Organization

POCP_ORG_NAME = "PoCP AI Commons"

GENESIS_MANIFESTO_PRIMARY = "GENESIS.md"

GENESIS_MANIFESTO_PATHS = [
    "GENESIS.md",
    "docs/genesis/README.md",
    "docs/genesis/zh-CN.md",
]


def ensure_pocp_org_foundation(db: Session) -> None:
    """Idempotently record Rain as org founder/sponsor and manifesto author."""
    rain = db.get(Entity, RAIN_ID)
    org_entity = db.query(Entity).filter(Entity.name == POCP_ORG_NAME).first()
    if rain is None or org_entity is None:
        return

    org_entity.owner_id = rain.id
    org_entity.creator_id = rain.id
    org_meta = dict(org_entity.metadata_ or {})
    org_meta.update(
        {
            "founded_by_entity_id": rain.id,
            "founded_by_name": rain.name,
            "primary_sponsor_entity_id": rain.id,
            "genesis_manifesto_paths": GENESIS_MANIFESTO_PATHS,
            "genesis_manifesto_primary": GENESIS_MANIFESTO_PRIMARY,
            "platform_language": "en",
        }
    )
    org_entity.metadata_ = org_meta

    org_row = db.query(Organization).filter(Organization.entity_id == org_entity.id).first()
    if org_row is not None:
        cfg = dict(org_row.config or {})
        cfg.update(
            {
                "founder_id": rain.id,
                "primary_sponsor_id": rain.id,
                "genesis_manifesto": GENESIS_MANIFESTO_PATHS,
                "mission": "AI Commons for verifiable contributions",
                "governance_note": (
                    "Rain founded the organization and drafted the Genesis manifesto; "
                    "Bob serves as governance proxy for human review in the demo loop."
                ),
            }
        )
        org_row.config = cfg

    rain_meta = dict(rain.metadata_ or {})
    roles = list(rain_meta.get("roles") or [])
    for role in (
        "founder",
        "maintainer",
        "protocol_initiator",
        "org_founder",
        "primary_sponsor",
        "genesis_manifesto_author",
    ):
        if role not in roles:
            roles.append(role)
    rain_meta["roles"] = roles
    rain_meta["org_founded"] = POCP_ORG_NAME
    rain_meta["org_entity_id"] = org_entity.id
    rain_meta["genesis_manifesto_primary"] = GENESIS_MANIFESTO_PRIMARY
    rain_meta["platform_language"] = "en"
    rain.metadata_ = rain_meta
    rain.description = (
        "Founder of PoCP AI Commons; primary sponsor who established the organization "
        "and drafted the Genesis manifesto (canonical: GENESIS.md)."
    )

    db.flush()


def can_sponsor_as_organization(
    db: Session,
    org_entity_id: str,
    actor_entity_id: str,
) -> bool:
    """Whether actor may create tasks sponsored by the organization entity."""
    org_entity = db.query(Entity).filter(Entity.id == org_entity_id).first()
    if org_entity is None or org_entity.entity_type != EntityType.organization:
        return False

    if actor_entity_id == org_entity.owner_id or actor_entity_id == org_entity.creator_id:
        return True

    org_row = db.query(Organization).filter(Organization.entity_id == org_entity_id).first()
    if org_row is None:
        return False

    if org_row.governance_proxy_id == actor_entity_id:
        return True

    cfg = org_row.config or {}
    if actor_entity_id in (
        cfg.get("founder_id"),
        cfg.get("primary_sponsor_id"),
    ):
        return True

    return actor_entity_id == RAIN_ID
