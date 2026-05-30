"""Code contribution registry: who built which paths, report, ledger, reputation."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from models.code_attribution import AttributionSource, CodeAttributionRecord
from models.entity import Entity, EntityStatus, EntityType
from models.ledger import LedgerRecord
from services.ledger_chain import append_ledger_record

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "config" / "code_attribution.yaml"

SKIP_DIRS = {
    "__pycache__",
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "data",
    "_patch_staging",
}

SKIP_EXTENSIONS = {".pyc", ".db", ".png", ".jpg", ".woff", ".woff2"}


def load_registry() -> dict[str, Any]:
    with REGISTRY_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def list_builders() -> list[dict[str, Any]]:
    data = load_registry()
    return [{"slug": slug, **spec} for slug, spec in (data.get("builders") or {}).items()]


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def match_builders_for_path(path: str) -> list[str]:
    """Return builder slugs whose path_rules match this file."""
    data = load_registry()
    normalized = _normalize_path(path)
    matched: list[str] = []
    for rule in data.get("path_rules") or []:
        slug = rule.get("builder")
        if not slug:
            continue
        for pattern in rule.get("patterns") or []:
            pat = _normalize_path(pattern)
            if pat.endswith("/"):
                if normalized.startswith(pat) or normalized.startswith(pat.rstrip("/") + "/"):
                    matched.append(slug)
                    break
            elif fnmatch.fnmatch(normalized, pat) or normalized == pat:
                matched.append(slug)
                break
    return list(dict.fromkeys(matched))


def scan_repository(root: Path | None = None) -> dict[str, Any]:
    """Scan repo files and aggregate line counts per builder."""
    root = root or Path(__file__).resolve().parents[2]
    builders: dict[str, dict[str, Any]] = {}
    unassigned: list[dict[str, Any]] = []

    data = load_registry()
    for slug, spec in (data.get("builders") or {}).items():
        builders[slug] = {
            "slug": slug,
            "display_name": spec.get("display_name", slug),
            "entity_id": spec.get("entity_id"),
            "entity_type": spec.get("entity_type"),
            "status": spec.get("status"),
            "roles": spec.get("roles", []),
            "summary": spec.get("summary", ""),
            "files": [],
            "lines": 0,
        }

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            full = Path(dirpath) / filename
            if full.suffix.lower() in SKIP_EXTENSIONS:
                continue
            rel = _normalize_path(str(full.relative_to(root)))
            if rel.startswith("_patch_staging"):
                continue
            try:
                text = full.read_text(encoding="utf-8", errors="ignore")
                line_count = len(text.splitlines()) or 1
            except OSError:
                continue

            slugs = match_builders_for_path(rel)
            entry = {"path": rel, "lines": line_count}
            if not slugs:
                residual = (data.get("attribution_policy") or {}).get("residual_builder")
                if residual and residual in builders:
                    slugs = [residual]
                    entry["attribution"] = (data.get("attribution_policy") or {}).get(
                        "residual_note", "residual"
                    )
                else:
                    unassigned.append(entry)
                    continue
            for slug in slugs:
                if slug not in builders:
                    continue
                builders[slug]["files"].append(entry)
                builders[slug]["lines"] += line_count

    for slug in builders:
        builders[slug]["file_count"] = len(builders[slug]["files"])

    return {
        "spec_version": data.get("spec_version", "0.1"),
        "root": str(root),
        "builders": builders,
        "unassigned_file_count": len(unassigned),
        "unassigned_lines": sum(u["lines"] for u in unassigned),
        "unassigned_sample": unassigned[:30],
    }


def ensure_builder_entities(db: Session) -> list[Entity]:
    """Create Entity rows for registry builders that have entity_id."""
    data = load_registry()
    created: list[Entity] = []
    type_map = {
        "agent": EntityType.agent,
        "llm": EntityType.llm,
        "human": EntityType.human,
        "skill": EntityType.skill,
    }

    for slug, spec in (data.get("builders") or {}).items():
        entity_id = spec.get("entity_id")
        if not entity_id:
            continue
        entity = db.get(Entity, entity_id)
        if entity is None:
            entity = Entity(
                id=entity_id,
                entity_type=type_map.get(spec.get("entity_type", "agent"), EntityType.agent),
                name=spec.get("display_name", slug),
                description=(spec.get("summary") or "")[:500],
                status=EntityStatus.active,
                metadata_={
                    "builder_slug": slug,
                    "roles": spec.get("roles", []),
                    "attribution_status": spec.get("status", "inferred"),
                    "registry": "code_attribution.yaml",
                },
            )
            db.add(entity)
            created.append(entity)
        else:
            entity.name = spec.get("display_name", slug)
            entity.metadata_ = {
                **(entity.metadata_ or {}),
                "builder_slug": slug,
                "roles": spec.get("roles", []),
                "attribution_status": spec.get("status", "inferred"),
            }
    db.flush()
    return created


def sync_scan_to_records(db: Session, root: Path | None = None) -> dict[str, int]:
    """Persist scan results as CodeAttributionRecord rows (idempotent per path+builder)."""
    report = scan_repository(root)
    counts = {"inserted": 0, "skipped": 0}

    for slug, info in report["builders"].items():
        entity_id = info.get("entity_id")
        for file_info in info["files"]:
            path = file_info["path"]
            exists = (
                db.query(CodeAttributionRecord)
                .filter(
                    CodeAttributionRecord.builder_slug == slug,
                    CodeAttributionRecord.path == path,
                    CodeAttributionRecord.source == AttributionSource.scan_inferred.value,
                )
                .first()
            )
            if exists:
                counts["skipped"] += 1
                continue
            db.add(
                CodeAttributionRecord(
                    builder_slug=slug,
                    entity_id=entity_id,
                    path=path,
                    lines_count=file_info["lines"],
                    source=AttributionSource.scan_inferred,
                    status=info.get("status", "inferred"),
                )
            )
            counts["inserted"] += 1
    db.flush()
    return counts


def award_registry_reputation(db: Session) -> dict[str, float]:
    """Grant reputation from scanned file counts (capped per builder)."""
    from models.wallet import ReputationScore
    from services.reputation_audit import record_reputation_audit

    data = load_registry()
    policy = data.get("reward_policy") or {}
    per_file = float(policy.get("registry_reputation_per_file", 0.5))
    cap = float(policy.get("registry_reputation_cap_per_builder", 200))
    awarded: dict[str, float] = {}

    report = scan_repository()
    for slug, info in report["builders"].items():
        entity_id = info.get("entity_id")
        if not entity_id:
            continue
        amount = min(cap, round(info["file_count"] * per_file, 2))
        if amount <= 0:
            continue
        rep = (
            db.query(ReputationScore)
            .filter(
                ReputationScore.entity_id == entity_id,
                ReputationScore.category == "code_registry",
            )
            .first()
        )
        if rep is None:
            rep = ReputationScore(entity_id=entity_id, score=amount, category="code_registry")
            db.add(rep)
            delta = amount
        else:
            delta = amount - rep.score
            rep.score = amount
        db.flush()
        record_reputation_audit(
            db,
            entity_id=entity_id,
            category="code_registry",
            delta=delta,
            balance_after=rep.score,
            source="code_attribution_sync",
            reason="Registry scan reputation bootstrap",
            reference_id=slug,
        )
        awarded[slug] = amount
    return awarded


def append_code_attribution_ledger(db: Session, summary: dict[str, Any]) -> LedgerRecord:
    data = load_registry()
    event_type = (data.get("reward_policy") or {}).get("ledger_event_type", "code_attribution_sync")
    return append_ledger_record(
        db,
        event_type=event_type,
        payload={"code_attribution_sync": summary},
        contribution_id=None,
    )
