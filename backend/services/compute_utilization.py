"""Provider utilization metrics — detect idle compute (v0.3)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity, EntityStatus
from services.compute_jobs import count_recent_jobs_for_provider
from services.compute_profile import get_compute_profile, is_profile_stale, list_compute_provider_entities
from services.compute_artifact import list_artifacts
from services.protocol_config import get_rewards_config


def _surplus_cfg() -> dict[str, Any]:
    return get_rewards_config().get("compute_surplus") or {}


def idle_window_hours() -> float:
    return float(_surplus_cfg().get("idle_window_hours") or 1.0)


def idle_job_threshold() -> int:
    return int(_surplus_cfg().get("idle_job_threshold") or 0)


def provider_utilization(
    db: Session,
    provider_entity_id: str,
    *,
    window_hours: float | None = None,
) -> dict[str, Any]:
    window = window_hours if window_hours is not None else idle_window_hours()
    jobs = count_recent_jobs_for_provider(db, provider_entity_id, since_hours=window)
    entity = db.get(Entity, provider_entity_id)
    profile = get_compute_profile(entity) if entity else None
    max_concurrent = int(((profile or {}).get("capacity") or {}).get("max_concurrent") or 1)
    utilization = min(jobs / max(max_concurrent, 1), 1.0)
    idle = jobs <= idle_job_threshold()
    return {
        "provider_entity_id": provider_entity_id,
        "recent_jobs": jobs,
        "window_hours": window,
        "max_concurrent": max_concurrent,
        "utilization": round(utilization, 4),
        "idle": idle,
        "profile_status": (profile or {}).get("status"),
        "stale": is_profile_stale(profile) if profile else True,
    }


def list_idle_providers(
    db: Session,
    *,
    organization_entity_id: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    rows = list_compute_provider_entities(
        db, status="active", mesh_filter=False, organization_entity_id=organization_entity_id
    )
    idle: list[dict[str, Any]] = []
    for row in rows:
        entity_id = row["entity_id"]
        profile = row.get("compute_profile") or {}
        if is_profile_stale(profile):
            continue
        stats = provider_utilization(db, entity_id)
        if stats["idle"]:
            idle.append({**stats, "entity_name": row.get("name")})
            if len(idle) >= limit:
                break
    return idle


def balance_summary(db: Session, *, organization_entity_id: str | None = None) -> dict[str, Any]:
    from services.compute_pool import get_pool_summary

    providers = list_compute_provider_entities(db, status="active", mesh_filter=False)
    utilizations = [provider_utilization(db, row["entity_id"]) for row in providers[:50]]
    idle_count = sum(1 for u in utilizations if u["idle"] and not u["stale"])
    avg_util = (
        sum(u["utilization"] for u in utilizations) / len(utilizations) if utilizations else 0.0
    )
    pool = get_pool_summary(db, organization_entity_id) if organization_entity_id else None
    artifacts = list_artifacts(limit=1000)
    return {
        "active_providers": len(providers),
        "idle_providers": idle_count,
        "average_utilization": round(avg_util, 4),
        "artifact_count": len(artifacts),
        "pool": pool,
        "recommendation": _recommendation(idle_count, avg_util, pool),
    }


def _recommendation(idle_count: int, avg_util: float, pool: dict | None) -> str:
    if idle_count > 0 and avg_util < 0.3:
        return "surplus_detected_run_recycle"
    if pool and float(pool.get("balance_credits") or 0) < float(pool.get("deficit_burst_limit") or 0) * 0.2:
        return "pool_low_sponsor_deposit"
    if avg_util > 0.85:
        return "deficit_escalate_purchase"
    return "balanced"
