"""External inspiration registry API — borrowed OSS projects as community entities."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.external_inspiration import ExternalInspirationRecord
from routers.auth import require_current_user
from services.external_inspiration import (
    append_inspiration_ledger,
    build_external_inspirations_context,
    build_inspiration_report,
    ensure_inspiration_entities,
    get_entity_inspiration_detail,
    get_inspiration,
    list_inspirations,
    match_inspirations_for_module,
    load_registry,
    sync_registry_to_records,
)

router = APIRouter(prefix="/api/v1/external-inspirations", tags=["external-inspirations"])


class ModuleMatchIn(BaseModel):
    module_path: str


class SyncIn(BaseModel):
    write_ledger: bool = True


@router.get("/registry")
def get_registry():
    data = load_registry()
    inspirations = data.get("inspirations") or {}
    return {
        "spec_version": data.get("spec_version"),
        "registry": data.get("registry"),
        "inspiration_count": len(inspirations),
        "contribution_count": sum(
            len(v.get("contributions") or []) for v in inspirations.values()
        ),
        "attribution_policy": data.get("attribution_policy"),
    }


@router.get("/inspirations")
def get_inspirations(include_declined: bool = False):
    return {"inspirations": list_inspirations(include_declined=include_declined)}


@router.get("/inspirations/{slug}")
def get_inspiration_detail(slug: str):
    item = get_inspiration(slug)
    if item is None:
        raise HTTPException(status_code=404, detail="Inspiration not found")
    return item


@router.get("/report")
def inspiration_report(db: Session = Depends(get_db)):
    return build_inspiration_report(db)


@router.post("/match")
def match_module(body: ModuleMatchIn):
    matches = match_inspirations_for_module(body.module_path)
    return {"module_path": body.module_path, "matches": matches}


@router.get("/records")
def list_records(db: Session = Depends(get_db), limit: int = 200):
    rows = (
        db.query(ExternalInspirationRecord)
        .order_by(ExternalInspirationRecord.recorded_at.desc())
        .limit(min(limit, 1000))
        .all()
    )
    return [
        {
            "id": r.id,
            "inspiration_slug": r.inspiration_slug,
            "contribution_id": r.contribution_id,
            "entity_id": r.entity_id,
            "title": r.title,
            "relationship": r.relationship,
            "status": r.status,
            "pocp_modules": r.pocp_modules or [],
            "api_paths": r.api_paths or [],
            "proof_layers": r.proof_layers or [],
            "integration_section": r.integration_section,
            "recorded_at": r.recorded_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/context")
def inspiration_context(module: str | None = None):
    hints = [module] if module else None
    return build_external_inspirations_context(None, module_hints=hints)


@router.get("/entities/{entity_id}")
def inspiration_entity_detail(entity_id: str, db: Session = Depends(get_db)):
    detail = get_entity_inspiration_detail(db, entity_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Not an external inspiration entity")
    return detail


@router.post("/sync")
def sync_inspirations(
    body: SyncIn,
    db: Session = Depends(get_db),
    _user=Depends(require_current_user),
):
    """Ensure inspiration entities, persist contribution records, optional ledger."""
    ensure_inspiration_entities(db)
    counts = sync_registry_to_records(db)
    report = build_inspiration_report(db)
    summary = {
        "records": counts,
        "inspiration_count": report["inspiration_count"],
        "contribution_count": report["contribution_count"],
    }
    ledger_id = None
    if body.write_ledger:
        record = append_inspiration_ledger(db, summary)
        ledger_id = record.id
        summary["ledger_record_id"] = ledger_id
    db.commit()
    return summary
