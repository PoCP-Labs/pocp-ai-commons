"""Community partner outreach — OSS & distributed communities as capability Entities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from datetime import datetime, timezone

from models.entity import Entity, EntityStatus, EntityType
from models.ledger import LedgerRecord
from services.ledger_chain import append_ledger_record
from services.org_foundation import POCP_ORG_NAME

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "config" / "community_partners.yaml"

ACTIVE_STATUSES = frozenset(
    {"active_partner", "federation_peer", "integrated", "in_conversation"}
)
SEEKING_STATUSES = frozenset({"prospect", "outreach", "in_conversation"})
PRIORITY_WEIGHT = {"high": 1.0, "medium": 0.7, "low": 0.4}
VALID_OUTREACH_EVENTS = frozenset(
    {
        "contact_sent",
        "response_received",
        "meeting_scheduled",
        "proposal_shared",
        "status_advanced",
        "note",
    }
)
VALID_STATUS_TRANSITIONS = frozenset(
    {
        "prospect",
        "outreach",
        "in_conversation",
        "active_partner",
        "federation_peer",
        "integrated",
        "paused",
    }
)
RUNTIME_PARTNER_METADATA_KEYS = frozenset(
    {"partnership_status", "outreach_log", "last_outreach_at"}
)


def load_registry() -> dict[str, Any]:
    with REGISTRY_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def list_partners(*, include_declined: bool = False) -> list[dict[str, Any]]:
    data = load_registry()
    items = [{"slug": slug, **spec} for slug, spec in (data.get("partners") or {}).items()]
    if include_declined:
        for slug, spec in (data.get("declined_partners") or {}).items():
            items.append({"slug": slug, **spec, "declined": True})
    return items


def get_partner(slug: str) -> dict[str, Any] | None:
    data = load_registry()
    spec = (data.get("partners") or {}).get(slug)
    if spec:
        return {"slug": slug, **spec}
    spec = (data.get("declined_partners") or {}).get(slug)
    if spec:
        return {"slug": slug, **spec, "declined": True}
    return None


def find_partner_by_entity_id(entity_id: str) -> dict[str, Any] | None:
    data = load_registry()
    for section in ("partners", "declined_partners"):
        for slug, spec in (data.get(section) or {}).items():
            if spec.get("entity_id") == entity_id:
                item = {"slug": slug, **spec}
                if section == "declined_partners":
                    item["declined"] = True
                return item
    return None


def _preserve_runtime_partner_metadata(
    existing: dict[str, Any] | None,
    base: dict[str, Any],
) -> dict[str, Any]:
    """Keep outreach-derived fields when refreshing from YAML."""
    existing = existing or {}
    merged = {**base}
    for key in RUNTIME_PARTNER_METADATA_KEYS:
        if existing.get(key) is not None:
            merged[key] = existing[key]
    return merged


def _overlay_partner_runtime(db: Session, row: dict[str, Any]) -> dict[str, Any]:
    entity_id = row.get("entity_id")
    if not entity_id:
        return row
    entity = db.get(Entity, entity_id)
    if entity is None:
        return row
    meta = entity.metadata_ or {}
    updated = dict(row)
    if meta.get("partnership_status"):
        updated["partnership_status"] = meta["partnership_status"]
    if meta.get("last_outreach_at"):
        updated["last_outreach_at"] = meta["last_outreach_at"]
    log = meta.get("outreach_log") or []
    if log:
        updated["outreach_log_count"] = len(log)
    return updated


def _partner_metadata(slug: str, spec: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    outreach = spec.get("outreach") or {}
    return {
        "partner_slug": slug,
        "registry": "community_partners.yaml",
        "community_kind": spec.get("community_kind"),
        "partnership_status": spec.get("partnership_status"),
        "outreach_priority": spec.get("outreach_priority"),
        "portable_id": spec.get("portable_id"),
        "github_url": spec.get("github_url"),
        "homepage_url": spec.get("homepage_url"),
        "inspiration_slug": spec.get("inspiration_slug"),
        "oss_slug": spec.get("oss_slug"),
        "alignment": spec.get("alignment") or [],
        "capabilities_offered": spec.get("capabilities_offered") or [],
        "capabilities_sought": spec.get("capabilities_sought") or [],
            "outreach_channel": outreach.get("channel"),
            "outreach_contact_url": outreach.get("contact_url"),
            "outreach_template_doc": outreach.get("template_doc"),
            "outreach_next_action": outreach.get("next_action"),
        "roles": ["community_partner", "community"],
        "decline_reason": spec.get("reason"),
    }


def ensure_partner_entities(db: Session, *, include_declined: bool = False) -> list[Entity]:
    """Create or refresh community Entity rows for partner registry."""
    data = load_registry()
    org = _pocp_org_entity(db)
    created: list[Entity] = []
    sections: list[tuple[str, dict[str, Any]]] = list((data.get("partners") or {}).items())
    if include_declined:
        sections.extend((data.get("declined_partners") or {}).items())

    for slug, spec in sections:
        entity_id = spec.get("entity_id")
        if not entity_id or len(str(entity_id)) > 36:
            continue
        metadata = _partner_metadata(slug, spec, data)
        entity = db.get(Entity, entity_id)
        if entity is None:
            entity = Entity(
                id=entity_id,
                entity_type=EntityType.community,
                name=spec.get("display_name", slug),
                description=(spec.get("summary") or spec.get("reason") or "")[:500],
                status=EntityStatus.inactive if spec.get("partnership_status") == "declined" else EntityStatus.active,
                metadata_=metadata,
            )
            db.add(entity)
            created.append(entity)
        else:
            entity.name = spec.get("display_name", slug)
            if spec.get("summary"):
                entity.description = spec["summary"][:500]
            entity.metadata_ = _preserve_runtime_partner_metadata(entity.metadata_, metadata)
            if spec.get("partnership_status") == "declined":
                entity.status = EntityStatus.inactive
        if org is not None:
            entity.creator_id = org.id

    db.flush()
    return created


def _pocp_org_entity(db: Session) -> Entity | None:
    return db.query(Entity).filter(Entity.name == POCP_ORG_NAME).first()


def match_partners_for_capability(capability: str) -> list[dict[str, Any]]:
    """Partners offering a PoCP capability (local or external community)."""
    normalized = capability.strip().lower()
    matched: list[dict[str, Any]] = []
    for partner in list_partners():
        if partner.get("declined"):
            continue
        for offer in partner.get("capabilities_offered") or []:
            if (offer.get("capability") or "").lower() == normalized:
                matched.append(
                    {
                        "slug": partner["slug"],
                        "display_name": partner.get("display_name"),
                        "entity_id": partner.get("entity_id"),
                        "partnership_status": partner.get("partnership_status"),
                        "community_kind": partner.get("community_kind"),
                        "capability": normalized,
                        "label": offer.get("label"),
                        "portable_id": partner.get("portable_id"),
                        "outreach_priority": partner.get("outreach_priority"),
                    }
                )
                break
    matched.sort(
        key=lambda p: PRIORITY_WEIGHT.get(p.get("outreach_priority") or "medium", 0.5),
        reverse=True,
    )
    return matched


def match_partners_seeking_capability(capability: str) -> list[dict[str, Any]]:
    """Partners that need a capability PoCP can offer — outreach opportunities."""
    normalized = capability.strip().lower()
    matched: list[dict[str, Any]] = []
    for partner in list_partners():
        if partner.get("declined"):
            continue
        for sought in partner.get("capabilities_sought") or []:
            if (sought.get("capability") or "").lower() == normalized:
                matched.append(
                    {
                        "slug": partner["slug"],
                        "display_name": partner.get("display_name"),
                        "entity_id": partner.get("entity_id"),
                        "partnership_status": partner.get("partnership_status"),
                        "capability": normalized,
                        "label": sought.get("label"),
                        "outreach_next_action": (partner.get("outreach") or {}).get("next_action"),
                    }
                )
                break
    return matched


def build_outreach_report(db: Session | None = None) -> dict[str, Any]:
    data = load_registry()
    partners = data.get("partners") or {}
    by_status: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    capability_offers: dict[str, int] = {}

    partner_rows: dict[str, Any] = {}
    for slug, spec in partners.items():
        status = spec.get("partnership_status", "prospect")
        kind = spec.get("community_kind", "oss_project")
        by_status[status] = by_status.get(status, 0) + 1
        by_kind[kind] = by_kind.get(kind, 0) + 1
        for offer in spec.get("capabilities_offered") or []:
            cap = offer.get("capability")
            if cap:
                capability_offers[cap] = capability_offers.get(cap, 0) + 1
        partner_rows[slug] = {
            "slug": slug,
            "display_name": spec.get("display_name", slug),
            "entity_id": spec.get("entity_id"),
            "community_kind": kind,
            "partnership_status": status,
            "outreach_priority": spec.get("outreach_priority"),
            "capabilities_offered": spec.get("capabilities_offered") or [],
            "capabilities_sought": spec.get("capabilities_sought") or [],
            "outreach": spec.get("outreach"),
            "alignment": spec.get("alignment") or [],
        }

    declined = {
        slug: {"slug": slug, **spec}
        for slug, spec in (data.get("declined_partners") or {}).items()
    }

    high_priority_prospects = [
        partner_rows[s]
        for s, spec in partners.items()
        if spec.get("outreach_priority") == "high"
        and spec.get("partnership_status") in SEEKING_STATUSES
    ]

    if db is not None:
        ensure_partner_entities(db)
        for slug in list(partner_rows.keys()):
            partner_rows[slug] = _overlay_partner_runtime(db, partner_rows[slug])
        by_status = {}
        for row in partner_rows.values():
            status = row.get("partnership_status", "prospect")
            by_status[status] = by_status.get(status, 0) + 1
        high_priority_prospects = [
            row
            for row in partner_rows.values()
            if row.get("outreach_priority") == "high"
            and row.get("partnership_status") in SEEKING_STATUSES
        ]

    return {
        "spec_version": data.get("spec_version", "0.1"),
        "registry": data.get("registry", "community_partners"),
        "partner_count": len(partners),
        "declined_count": len(declined),
        "by_status": by_status,
        "by_community_kind": by_kind,
        "capability_offer_counts": capability_offers,
        "outreach_policy": data.get("outreach_policy"),
        "partners": partner_rows,
        "declined_partners": declined,
        "high_priority_prospects": high_priority_prospects,
    }


def get_entity_partner_profile(db: Session, entity_id: str) -> dict[str, Any] | None:
    partner = find_partner_by_entity_id(entity_id)
    if partner is None:
        entity = db.get(Entity, entity_id)
        if entity is None:
            return None
        slug = (entity.metadata_ or {}).get("partner_slug")
        if slug:
            partner = get_partner(slug)
        if partner is None:
            return None
    resolved_entity_id = partner.get("entity_id") or entity_id
    entity = db.get(Entity, resolved_entity_id)
    runtime = entity.metadata_ if entity is not None else {}
    status = (runtime or {}).get("partnership_status") or partner.get("partnership_status")
    return {
        **partner,
        "entity_id": resolved_entity_id,
        "partnership_status": status,
        "last_outreach_at": (runtime or {}).get("last_outreach_at"),
        "outreach_log_count": len((runtime or {}).get("outreach_log") or []),
    }


def discover_capability_partners(
    db: Session,
    capability: str,
) -> dict[str, Any]:
    """Merge registry partners with on-node compute providers for a capability."""
    from services.compute_profile import list_compute_provider_entities

    external = match_partners_for_capability(capability)
    seeking = match_partners_seeking_capability(capability)
    local_rows = list_compute_provider_entities(db, capability=capability, status="active")
    local = [
        {
            "entity_id": e.id,
            "name": e.name,
            "source": "local_compute_profile",
            "partnership_status": "active_partner",
            "capability": capability,
        }
        for e in local_rows
    ]
    return {
        "capability": capability,
        "local_providers": local,
        "external_partners": external,
        "partners_seeking_this_capability": seeking,
        "discovery_note": "Combine local compute_profile with community partner registry for outreach.",
    }


def append_partner_graph_edges(
    db: Session,
    *,
    edges: list[dict],
    entity_map: dict[str, Entity],
    append_edge,
) -> None:
    """Link PoCP org to partner entities by partnership status."""
    org = _pocp_org_entity(db)
    if org is None:
        return

    for partner in list_partners():
        entity_id = partner.get("entity_id")
        if not entity_id or entity_id not in entity_map:
            continue
        status = partner.get("partnership_status", "prospect")
        priority = partner.get("outreach_priority", "medium")
        weight = PRIORITY_WEIGHT.get(priority, 0.5)

        if status in SEEKING_STATUSES:
            append_edge(
                edges,
                {
                    "source": org.id,
                    "target": entity_id,
                    "relation": "seeks_partnership",
                    "contribution_id": None,
                    "weight": weight,
                },
            )
        elif status in ACTIVE_STATUSES or status == "integrated":
            append_edge(
                edges,
                {
                    "source": org.id,
                    "target": entity_id,
                    "relation": "partners_with",
                    "contribution_id": None,
                    "weight": weight,
                },
            )

        for offer in partner.get("capabilities_offered") or []:
            cap = offer.get("capability")
            if not cap:
                continue
            append_edge(
                edges,
                {
                    "source": entity_id,
                    "target": org.id,
                    "relation": "offers_capability",
                    "contribution_id": None,
                    "weight": weight,
                },
            )


def append_partner_ledger(db: Session, summary: dict[str, Any]) -> LedgerRecord:
    return append_ledger_record(
        db,
        event_type="community_partner_sync",
        payload={"community_partner_sync": summary},
        contribution_id=None,
    )


def _task_keywords_from_contribution(contribution: Any) -> set[str]:
    task = getattr(contribution, "task", None)
    if task is None:
        return set()
    text = f"{task.title or ''} {task.description or ''}".lower()
    return {word for word in text.replace(",", " ").split() if len(word) > 2}


def build_community_partner_context(
    db: Session,
    contribution: Any,
    evidence: dict | None = None,
) -> dict[str, Any]:
    """Proof-layer context: partner communities aligned with this contribution."""
    from services.compute_matching import infer_required_capabilities

    evidence = evidence or getattr(contribution, "evidence", None) or {}
    task_keywords = _task_keywords_from_contribution(contribution)
    if evidence:
        meta = evidence.get("_pocp") or {}
        for key in ("tags", "topics", "keywords"):
            val = meta.get(key)
            if isinstance(val, list):
                task_keywords.update(str(v).lower() for v in val)

    required = infer_required_capabilities(
        task_keywords=task_keywords,
        contribution_type=getattr(contribution, "contribution_type", None),
    )
    capability_discovery: dict[str, Any] = {}
    matched_slugs: set[str] = set()
    matched_partners: list[dict[str, Any]] = []

    for item in required[:4]:
        cap = item["capability"]
        if db is None:
            capability_discovery[cap] = {"need_score": item.get("need_score"), "skipped": "no_db"}
            for partner in match_partners_for_capability(cap):
                slug = partner.get("slug")
                if slug and slug not in matched_slugs:
                    matched_slugs.add(slug)
                    matched_partners.append(partner)
            continue
        discovery = discover_capability_partners(db, cap)
        capability_discovery[cap] = {
            "need_score": item.get("need_score"),
            "local_count": len(discovery.get("local_providers") or []),
            "external_count": len(discovery.get("external_partners") or []),
            "seeking_count": len(discovery.get("partners_seeking_this_capability") or []),
            "external_partners": (discovery.get("external_partners") or [])[:5],
        }
        for partner in discovery.get("external_partners") or []:
            slug = partner.get("slug")
            if slug and slug not in matched_slugs:
                matched_slugs.add(slug)
                matched_partners.append(partner)

    primary_id = getattr(contribution, "primary_entity_id", None)
    primary_partner = get_entity_partner_profile(db, primary_id) if primary_id and db else None

    report = build_outreach_report(db) if db else {"outreach_policy": load_registry().get("outreach_policy"), "high_priority_prospects": []}
    return {
        "spec_version": "pocp.community_partner_context.v0.1",
        "outreach_principle": (report.get("outreach_policy") or {}).get("principle"),
        "primary_entity_partner": primary_partner,
        "inferred_capabilities": required,
        "capability_discovery": capability_discovery,
        "matched_partners": matched_partners[:12],
        "high_priority_outreach": (report.get("high_priority_prospects") or [])[:8],
        "note": "Advisory partner map for federated OSS outreach — not endorsement.",
    }


def get_contribution_partner_context(
    db: Session,
    contribution: Any,
) -> dict[str, Any]:
    ctx = build_community_partner_context(db, contribution, contribution.evidence)
    ctx["contribution_id"] = contribution.id
    ctx["compat"] = "pocp.community_partner_context.v0.1"
    return ctx


def get_partner_outreach_log(db: Session, slug: str) -> list[dict[str, Any]]:
    partner = get_partner(slug)
    if partner is None:
        return []
    entity_id = partner.get("entity_id")
    if not entity_id:
        return []
    entity = db.get(Entity, entity_id)
    if entity is None:
        return []
    return list((entity.metadata_ or {}).get("outreach_log") or [])


def record_partner_outreach(
    db: Session,
    slug: str,
    *,
    event_type: str,
    notes: str = "",
    new_status: str | None = None,
    actor_entity_id: str | None = None,
) -> dict[str, Any]:
    """Append outreach event to partner Entity metadata and ledger."""
    partner = get_partner(slug)
    if partner is None:
        raise ValueError(f"Partner not found: {slug}")
    if partner.get("declined"):
        raise ValueError(f"Partner declined: {slug}")

    event_type = event_type.strip().lower()
    if event_type not in VALID_OUTREACH_EVENTS:
        raise ValueError(f"Invalid outreach event_type: {event_type}")

    entity_id = partner.get("entity_id")
    if not entity_id:
        raise ValueError(f"Partner has no entity_id: {slug}")

    ensure_partner_entities(db)
    entity = db.get(Entity, entity_id)
    if entity is None:
        raise ValueError(f"Partner entity missing: {entity_id}")

    metadata = dict(entity.metadata_ or {})
    previous_status = metadata.get("partnership_status") or partner.get("partnership_status")
    if new_status:
        new_status = new_status.strip()
        if new_status not in VALID_STATUS_TRANSITIONS:
            raise ValueError(f"Invalid partnership status: {new_status}")
        metadata["partnership_status"] = new_status

    entry = {
        "at": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "notes": notes[:2000],
        "actor_entity_id": actor_entity_id,
        "previous_status": previous_status,
        "new_status": metadata.get("partnership_status", previous_status),
        "partner_slug": slug,
    }
    log = list(metadata.get("outreach_log") or [])
    log.insert(0, entry)
    metadata["outreach_log"] = log[:50]
    metadata["last_outreach_at"] = entry["at"]
    entity.metadata_ = metadata
    db.flush()

    ledger = append_ledger_record(
        db,
        event_type="partner_outreach_event",
        payload={"partner_outreach": entry},
        contribution_id=None,
    )
    return {"entry": entry, "ledger_record_id": ledger.id, "outreach_log": metadata["outreach_log"]}
