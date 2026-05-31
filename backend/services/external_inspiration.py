"""External inspiration registry: borrowed OSS patterns as community entities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from models.entity import Entity, EntityStatus, EntityType
from models.external_inspiration import ExternalInspirationRecord, InspirationRecordSource
from models.ledger import LedgerRecord
from services.ledger_chain import append_ledger_record
from services.org_foundation import POCP_ORG_NAME

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "config" / "external_inspirations.yaml"
CONTRIBUTION_HUB_PREFIX = "contribution:"


def load_registry() -> dict[str, Any]:
    with REGISTRY_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def list_inspirations(*, include_declined: bool = False) -> list[dict[str, Any]]:
    data = load_registry()
    items = [
        {"slug": slug, **spec}
        for slug, spec in (data.get("inspirations") or {}).items()
    ]
    if include_declined:
        for slug, spec in (data.get("declined_inspirations") or {}).items():
            items.append({"slug": slug, **spec, "declined": True})
    return items


def get_inspiration(slug: str) -> dict[str, Any] | None:
    data = load_registry()
    spec = (data.get("inspirations") or {}).get(slug)
    if spec:
        return {"slug": slug, **spec}
    spec = (data.get("declined_inspirations") or {}).get(slug)
    if spec:
        return {"slug": slug, **spec, "declined": True}
    return None


def match_inspirations_for_module(module_path: str) -> list[dict[str, Any]]:
    """Return inspiration slugs whose contributions reference this module path."""
    normalized = module_path.replace("\\", "/").lstrip("./")
    matched: list[dict[str, Any]] = []
    data = load_registry()
    for slug, spec in (data.get("inspirations") or {}).items():
        for contrib in spec.get("contributions") or []:
            modules = contrib.get("pocp_modules") or []
            for mod in modules:
                mod_norm = mod.replace("\\", "/").lstrip("./")
                if normalized == mod_norm or normalized.startswith(mod_norm.rstrip("/") + "/"):
                    matched.append(
                        {
                            "slug": slug,
                            "display_name": spec.get("display_name", slug),
                            "entity_id": spec.get("entity_id"),
                            "contribution_id": contrib.get("id"),
                            "title": contrib.get("title"),
                            "portable_id": spec.get("portable_id"),
                        }
                    )
                    break
    return matched


def _pocp_org_entity(db: Session) -> Entity | None:
    return db.query(Entity).filter(Entity.name == POCP_ORG_NAME).first()


def find_inspiration_by_entity_id(entity_id: str) -> dict[str, Any] | None:
    data = load_registry()
    for section in ("inspirations", "declined_inspirations"):
        for slug, spec in (data.get(section) or {}).items():
            if spec.get("entity_id") == entity_id:
                item = {"slug": slug, **spec}
                if section == "declined_inspirations":
                    item["declined"] = True
                return item
    return None


def get_entity_inspiration_detail(db: Session, entity_id: str) -> dict[str, Any] | None:
    """Full inspiration profile for a community entity."""
    spec = find_inspiration_by_entity_id(entity_id)
    if spec is None:
        entity = db.get(Entity, entity_id)
        if entity is None or entity.entity_type != EntityType.community:
            return None
        slug = (entity.metadata_ or {}).get("inspiration_slug")
        if slug:
            spec = get_inspiration(slug)
        if spec is None:
            return None

    slug = spec["slug"]
    records = (
        db.query(ExternalInspirationRecord)
        .filter(ExternalInspirationRecord.inspiration_slug == slug)
        .order_by(ExternalInspirationRecord.contribution_id)
        .all()
    )
    return {
        **spec,
        "entity_id": spec.get("entity_id") or entity_id,
        "recorded_contributions": [
            {
                "id": r.id,
                "contribution_id": r.contribution_id,
                "title": r.title,
                "pocp_modules": r.pocp_modules or [],
                "api_paths": r.api_paths or [],
                "proof_layers": r.proof_layers or [],
                "integration_section": r.integration_section,
                "recorded_at": r.recorded_at.isoformat(),
            }
            for r in records
        ],
    }


def get_inspirations_for_contribution(
    db: Session,
    evidence: dict | None,
) -> dict[str, Any]:
    """Resolve matched inspirations for a contribution's evidence."""
    context = build_external_inspirations_context(evidence)
    matched = context.get("matched_from_evidence") or []
    if not matched:
        return {
            "compat": "pocp.external_inspirations.v0.1",
            "matched_count": 0,
            "inspirations": [],
            "context": context,
        }

    enriched = []
    for item in matched:
        slug = item.get("slug")
        detail = get_inspiration(slug) if slug else None
        enriched.append(
            {
                **item,
                "github_url": (detail or {}).get("github_url"),
                "integration_round": (detail or {}).get("integration_round"),
                "status": (detail or {}).get("status"),
            }
        )
    return {
        "compat": "pocp.external_inspirations.v0.1",
        "matched_count": len(enriched),
        "inspirations": enriched,
        "context": context,
    }


def append_inspiration_graph_edges(
    db: Session,
    *,
    edges: list[dict],
    nodes: list[dict],
    node_ids: set[str],
    entity_map: dict[str, Entity],
    contributions: list[Any],
    append_edge,
) -> None:
    """Add learned_from / uses_pattern_from edges linking org and contributions to inspirations."""
    org = _pocp_org_entity(db)
    data = load_registry()

    for slug, spec in (data.get("inspirations") or {}).items():
        entity_id = spec.get("entity_id")
        if not entity_id or entity_id not in entity_map:
            continue
        if org is not None:
            append_edge(
                edges,
                {
                    "source": org.id,
                    "target": entity_id,
                    "relation": "learned_from",
                    "contribution_id": None,
                    "weight": 1.0,
                },
            )

    for contrib in contributions:
        hub_id = f"{CONTRIBUTION_HUB_PREFIX}{contrib.id}"
        if hub_id not in node_ids:
            continue
        context = build_external_inspirations_context(contrib.evidence)
        seen_targets: set[str] = set()
        for item in context.get("matched_from_evidence") or []:
            target_id = item.get("entity_id")
            if not target_id or target_id in seen_targets:
                continue
            if target_id not in entity_map:
                continue
            seen_targets.add(target_id)
            append_edge(
                edges,
                {
                    "source": hub_id,
                    "target": target_id,
                    "relation": "uses_pattern_from",
                    "contribution_id": contrib.id,
                    "weight": 1.0,
                },
            )


def ensure_inspiration_entities(db: Session, *, include_declined: bool = True) -> list[Entity]:
    """Create or refresh community Entity rows for registry inspirations."""
    data = load_registry()
    created: list[Entity] = []
    org = _pocp_org_entity(db)
    sections: list[tuple[str, dict[str, Any]]] = list((data.get("inspirations") or {}).items())
    if include_declined:
        sections.extend((data.get("declined_inspirations") or {}).items())

    for slug, spec in sections:
        entity_id = spec.get("entity_id")
        if not entity_id:
            continue
        entity = db.get(Entity, entity_id)
        metadata = {
            "inspiration_slug": slug,
            "portable_id": spec.get("portable_id"),
            "github_url": spec.get("github_url"),
            "homepage_url": spec.get("homepage_url"),
            "relationship": data.get("relationship_default", "pattern_borrowed"),
            "inspiration_status": spec.get("status", "pattern_borrowed"),
            "integration_round": spec.get("integration_round"),
            "registry": "external_inspirations.yaml",
            "roles": ["external_inspiration"],
        }
        if spec.get("reason"):
            metadata["decline_reason"] = spec["reason"]
        if entity is None:
            entity = Entity(
                id=entity_id,
                entity_type=EntityType.community,
                name=spec.get("display_name", slug),
                description=(spec.get("summary") or spec.get("reason") or "")[:500],
                status=EntityStatus.active,
                metadata_=metadata,
            )
            db.add(entity)
            created.append(entity)
        else:
            entity.name = spec.get("display_name", slug)
            entity.entity_type = EntityType.community
            entity.description = (spec.get("summary") or spec.get("reason") or entity.description or "")[:500]
            entity.metadata_ = {**(entity.metadata_ or {}), **metadata}
        if org is not None:
            entity.creator_id = org.id
    db.flush()
    return created


def sync_registry_to_records(db: Session) -> dict[str, int]:
    """Persist YAML contribution entries as ExternalInspirationRecord rows."""
    data = load_registry()
    counts = {"inserted": 0, "skipped": 0, "updated": 0}
    relationship = data.get("relationship_default", "pattern_borrowed")

    for slug, spec in (data.get("inspirations") or {}).items():
        entity_id = spec.get("entity_id")
        for contrib in spec.get("contributions") or []:
            contrib_id = contrib.get("id")
            if not contrib_id:
                continue
            existing = (
                db.query(ExternalInspirationRecord)
                .filter(
                    ExternalInspirationRecord.inspiration_slug == slug,
                    ExternalInspirationRecord.contribution_id == contrib_id,
                )
                .first()
            )
            if existing:
                existing.title = contrib.get("title", existing.title)
                existing.entity_id = entity_id
                existing.pocp_modules = contrib.get("pocp_modules") or []
                existing.api_paths = contrib.get("api_paths") or []
                existing.proof_layers = contrib.get("proof_layers") or []
                existing.integration_section = contrib.get("integration_section")
                existing.status = spec.get("status", "recorded")
                counts["updated"] += 1
                continue
            db.add(
                ExternalInspirationRecord(
                    inspiration_slug=slug,
                    contribution_id=contrib_id,
                    entity_id=entity_id,
                    title=contrib.get("title", contrib_id),
                    relationship=relationship,
                    status=spec.get("status", "recorded"),
                    pocp_modules=contrib.get("pocp_modules") or [],
                    api_paths=contrib.get("api_paths") or [],
                    proof_layers=contrib.get("proof_layers") or [],
                    integration_section=contrib.get("integration_section"),
                    source=InspirationRecordSource.registry.value,
                    metadata_={
                        "display_name": spec.get("display_name"),
                        "portable_id": spec.get("portable_id"),
                        "github_url": spec.get("github_url"),
                    },
                )
            )
            counts["inserted"] += 1
    db.flush()
    return counts


def build_inspiration_report(db: Session | None = None) -> dict[str, Any]:
    """Aggregate registry + optional DB records into a transparency report."""
    data = load_registry()
    inspirations = data.get("inspirations") or {}
    report_inspirations: dict[str, Any] = {}

    for slug, spec in inspirations.items():
        contributions = spec.get("contributions") or []
        report_inspirations[slug] = {
            "slug": slug,
            "display_name": spec.get("display_name", slug),
            "entity_id": spec.get("entity_id"),
            "portable_id": spec.get("portable_id"),
            "github_url": spec.get("github_url"),
            "status": spec.get("status"),
            "integration_round": spec.get("integration_round"),
            "summary": spec.get("summary", ""),
            "contribution_count": len(contributions),
            "contributions": contributions,
        }

    declined = {
        slug: {"slug": slug, **spec}
        for slug, spec in (data.get("declined_inspirations") or {}).items()
    }

    db_records: list[dict[str, Any]] = []
    if db is not None:
        rows = (
            db.query(ExternalInspirationRecord)
            .order_by(
                ExternalInspirationRecord.inspiration_slug,
                ExternalInspirationRecord.contribution_id,
            )
            .all()
        )
        db_records = [
            {
                "id": r.id,
                "inspiration_slug": r.inspiration_slug,
                "contribution_id": r.contribution_id,
                "entity_id": r.entity_id,
                "title": r.title,
                "relationship": r.relationship,
                "status": r.status,
                "pocp_modules": r.pocp_modules or [],
                "recorded_at": r.recorded_at.isoformat(),
            }
            for r in rows
        ]

    return {
        "spec_version": data.get("spec_version", "0.1"),
        "registry": data.get("registry", "external_inspirations"),
        "inspiration_count": len(report_inspirations),
        "contribution_count": sum(
            len(v.get("contributions") or []) for v in inspirations.values()
        ),
        "inspirations": report_inspirations,
        "declined_inspirations": declined,
        "attribution_policy": data.get("attribution_policy"),
        "persisted_records": db_records,
    }


def build_external_inspirations_context(
    evidence: dict | None = None,
    *,
    module_hints: list[str] | None = None,
) -> dict[str, Any]:
    """Proof-layer context: which external inspirations relate to this contribution."""
    hints: list[str] = list(module_hints or [])
    if evidence:
        meta = evidence.get("_pocp") or {}
        for key in ("code_paths", "modules", "files"):
            val = meta.get(key)
            if isinstance(val, list):
                hints.extend(str(v) for v in val)
            elif isinstance(val, str):
                hints.append(val)

    matched: dict[str, dict[str, Any]] = {}
    for hint in hints:
        for item in match_inspirations_for_module(hint):
            slug = item["slug"]
            if slug not in matched:
                insp = get_inspiration(slug)
                matched[slug] = {
                    "slug": slug,
                    "display_name": item.get("display_name"),
                    "entity_id": item.get("entity_id"),
                    "portable_id": item.get("portable_id") or (insp or {}).get("portable_id"),
                    "github_url": (insp or {}).get("github_url"),
                    "contributions": [],
                }
            contrib_entry = {
                "contribution_id": item.get("contribution_id"),
                "title": item.get("title"),
                "matched_module": hint,
            }
            if contrib_entry not in matched[slug]["contributions"]:
                matched[slug]["contributions"].append(contrib_entry)

    all_inspirations = list_inspirations()
    return {
        "spec_version": "pocp.external_inspirations.v0.1",
        "relationship": load_registry().get("relationship_default", "pattern_borrowed"),
        "matched_from_evidence": list(matched.values()),
        "registry_summary": [
            {
                "slug": i["slug"],
                "display_name": i.get("display_name"),
                "entity_id": i.get("entity_id"),
                "portable_id": i.get("portable_id"),
                "contribution_count": len(i.get("contributions") or []),
            }
            for i in all_inspirations
        ],
        "note": "PoCP records borrowed OSS patterns as community entities; no token-first imports.",
    }


def append_inspiration_ledger(db: Session, summary: dict[str, Any]) -> LedgerRecord:
    data = load_registry()
    event_type = (data.get("ledger_policy") or {}).get(
        "ledger_event_type", "external_inspiration_sync"
    )
    return append_ledger_record(
        db,
        event_type=event_type,
        payload={"external_inspiration_sync": summary},
        contribution_id=None,
    )
