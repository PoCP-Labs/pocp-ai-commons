"""Code attribution registry API — who built what, scan reports, sync to ledger."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.code_attribution import CodeAttributionRecord
from routers.auth import require_current_user
from services.code_attribution import (
    append_code_attribution_ledger,
    award_registry_reputation,
    ensure_builder_entities,
    list_builders,
    load_registry,
    match_builders_for_path,
    scan_repository,
    sync_scan_to_records,
)

router = APIRouter(prefix="/api/v1/code-attribution", tags=["code-attribution"])


class PathMatchIn(BaseModel):
    path: str


class SyncIn(BaseModel):
    award_reputation: bool = False
    write_ledger: bool = True


@router.get("/registry")
def get_registry():
    data = load_registry()
    return {
        "spec_version": data.get("spec_version"),
        "builders": data.get("builders"),
        "path_rules_count": len(data.get("path_rules") or []),
    }


@router.get("/builders")
def get_builders():
    return {"builders": list_builders()}


@router.post("/match")
def match_path(body: PathMatchIn):
    slugs = match_builders_for_path(body.path)
    data = load_registry()
    builders = data.get("builders") or {}
    return {
        "path": body.path,
        "builders": [
            {"slug": s, **{k: builders[s].get(k) for k in ("display_name", "entity_id", "entity_type", "status")}}
            for s in slugs
            if s in builders
        ],
    }


@router.get("/report")
def attribution_report():
    return scan_repository()


@router.get("/records")
def list_records(db: Session = Depends(get_db), limit: int = 200):
    rows = (
        db.query(CodeAttributionRecord)
        .order_by(CodeAttributionRecord.recorded_at.desc())
        .limit(min(limit, 1000))
        .all()
    )
    return [
        {
            "id": r.id,
            "builder_slug": r.builder_slug,
            "entity_id": r.entity_id,
            "path": r.path,
            "lines_count": r.lines_count,
            "source": r.source,
            "status": r.status,
            "recorded_at": r.recorded_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/sync")
def sync_attribution(
    body: SyncIn,
    db: Session = Depends(get_db),
    _user=Depends(require_current_user),
):
    """Scan repo, ensure builder entities, persist records, optional reputation + ledger."""
    ensure_builder_entities(db)
    counts = sync_scan_to_records(db)
    report = scan_repository()
    summary = {
        "records": counts,
        "builder_file_counts": {s: b["file_count"] for s, b in report["builders"].items()},
        "unassigned_file_count": report["unassigned_file_count"],
    }
    awarded = {}
    if body.award_reputation:
        awarded = award_registry_reputation(db)
        summary["reputation_awarded"] = awarded
    ledger_id = None
    if body.write_ledger:
        record = append_code_attribution_ledger(db, summary)
        ledger_id = record.id
        summary["ledger_record_id"] = ledger_id
    db.commit()
    return summary
