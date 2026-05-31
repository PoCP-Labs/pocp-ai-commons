"""Community partner outreach API — OSS & distributed community Entities."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from routers.auth import require_current_user
from services.community_partner import (
    append_partner_ledger,
    build_outreach_report,
    discover_capability_partners,
    ensure_partner_entities,
    get_entity_partner_profile,
    get_partner,
    get_partner_outreach_log,
    list_partners,
    load_registry,
    match_partners_for_capability,
    match_partners_seeking_capability,
    record_partner_outreach,
)

router = APIRouter(prefix="/api/v1/community-partners", tags=["community-partners"])


class SyncIn(BaseModel):
    write_ledger: bool = True


class OutreachEventIn(BaseModel):
    event_type: str = "contact_sent"
    notes: str = ""
    new_status: str | None = None


@router.get("/registry")
def get_registry():
    data = load_registry()
    partners = data.get("partners") or {}
    return {
        "spec_version": data.get("spec_version"),
        "registry": data.get("registry"),
        "partner_count": len(partners),
        "outreach_policy": data.get("outreach_policy"),
        "community_kinds": data.get("community_kinds"),
    }


@router.get("/partners")
def get_partners(include_declined: bool = False):
    return {"partners": list_partners(include_declined=include_declined)}


@router.get("/partners/{slug}")
def get_partner_detail(slug: str):
    item = get_partner(slug)
    if item is None:
        raise HTTPException(status_code=404, detail="Partner not found")
    return item


@router.get("/report")
def outreach_report(db: Session = Depends(get_db)):
    ensure_partner_entities(db)
    return build_outreach_report(db)


@router.get("/match")
def match_capability(capability: str):
    return {
        "capability": capability,
        "offers": match_partners_for_capability(capability),
        "seeks": match_partners_seeking_capability(capability),
    }


@router.get("/discover")
def discover_partners(capability: str, db: Session = Depends(get_db)):
    return discover_capability_partners(db, capability)


@router.get("/entities/{entity_id}")
def partner_entity_profile(entity_id: str, db: Session = Depends(get_db)):
    profile = get_entity_partner_profile(db, entity_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Not a community partner entity")
    return profile


@router.get("/partners/{slug}/outreach-log")
def partner_outreach_log(slug: str, db: Session = Depends(get_db)):
    if get_partner(slug) is None:
        raise HTTPException(status_code=404, detail="Partner not found")
    return {"slug": slug, "entries": get_partner_outreach_log(db, slug)}


@router.post("/partners/{slug}/outreach")
def log_partner_outreach(
    slug: str,
    body: OutreachEventIn,
    db: Session = Depends(get_db),
    user=Depends(require_current_user),
):
    try:
        result = record_partner_outreach(
            db,
            slug,
            event_type=body.event_type,
            notes=body.notes,
            new_status=body.new_status,
            actor_entity_id=user.entity_id,
        )
        db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sync")
def sync_partners(
    body: SyncIn,
    db: Session = Depends(get_db),
    _user=Depends(require_current_user),
):
    ensure_partner_entities(db, include_declined=True)
    report = build_outreach_report(db)
    summary = {
        "partner_count": report["partner_count"],
        "by_status": report["by_status"],
        "high_priority_prospects": len(report.get("high_priority_prospects") or []),
    }
    ledger_id = None
    if body.write_ledger:
        record = append_partner_ledger(db, summary)
        ledger_id = record.id
        summary["ledger_record_id"] = ledger_id
    db.commit()
    return summary
