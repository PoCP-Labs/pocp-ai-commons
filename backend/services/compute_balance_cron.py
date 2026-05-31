"""Auto balance cycle — surplus recycle from balance/summary (v0.4)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity, EntityType
from services.compute_precompute import recycle_surplus
from services.compute_profile import list_compute_provider_entities
from services.compute_utilization import balance_summary
from services.protocol_config import get_rewards_config

_last_auto_balance_run: dict[str, Any] | None = None


def _surplus_cfg() -> dict[str, Any]:
    return get_rewards_config().get("compute_surplus") or {}


def auto_balance_enabled() -> bool:
    env = os.getenv("POCP_COMPUTE_AUTO_BALANCE", "").lower()
    if env in ("1", "true", "yes"):
        return True
    if env in ("0", "false", "no"):
        return False
    return bool(_surplus_cfg().get("auto_balance_enabled", False))


def auto_balance_interval_minutes() -> int:
    env = os.getenv("POCP_COMPUTE_AUTO_BALANCE_INTERVAL_MINUTES")
    if env and env.isdigit():
        return max(int(env), 1)
    return max(int(_surplus_cfg().get("auto_balance_interval_minutes") or 60), 1)


def get_last_auto_balance_run() -> dict[str, Any] | None:
    return _last_auto_balance_run


def discover_balance_org_targets(db: Session) -> list[str | None]:
    """Org ids to run surplus recycle for; None = global unscoped providers."""
    org_ids: set[str] = set()
    has_unscoped = False

    for row in list_compute_provider_entities(db, status="active", mesh_filter=False):
        policy = (row.get("compute_profile") or {}).get("policy") or {}
        org_id = policy.get("organization_entity_id") or row.get("organization_entity_id")
        if org_id:
            org_ids.add(str(org_id))
        else:
            has_unscoped = True

    for entity in db.query(Entity).filter(Entity.entity_type == EntityType.organization):
        if (entity.metadata_ or {}).get("compute_pool"):
            org_ids.add(entity.id)

    targets: list[str | None] = sorted(org_ids)
    if has_unscoped:
        targets.append(None)
    return targets if targets else [None]


def run_auto_balance_cycle(
    db: Session,
    *,
    organization_entity_id: str | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Evaluate balance/summary and act on surplus (recycle) when configured."""
    global _last_auto_balance_run

    cfg = _surplus_cfg()
    if not cfg.get("enabled", True):
        result = {"status": "disabled", "reason": "compute_surplus.disabled"}
        _last_auto_balance_run = result
        return result

    if not auto_balance_enabled() and not dry_run and not force:
        result = {
            "status": "skipped",
            "reason": "auto_balance_disabled",
            "hint": "Set POCP_COMPUTE_AUTO_BALANCE=true or compute_surplus.auto_balance_enabled",
        }
        _last_auto_balance_run = result
        return result

    ran_at = datetime.now(timezone.utc).isoformat()
    targets = [organization_entity_id] if organization_entity_id else discover_balance_org_targets(db)
    actions: list[dict[str, Any]] = []

    for org_id in targets:
        summary = balance_summary(db, organization_entity_id=org_id)
        recommendation = summary["recommendation"]
        action: dict[str, Any] = {
            "organization_entity_id": org_id,
            "recommendation": recommendation,
            "idle_providers": summary.get("idle_providers"),
            "average_utilization": summary.get("average_utilization"),
        }

        if recommendation == "surplus_detected_run_recycle" and cfg.get("auto_recycle_on_surplus", True):
            if dry_run:
                action["action"] = "would_recycle"
            else:
                action["recycle"] = recycle_surplus(db, organization_entity_id=org_id)
                action["action"] = "recycled"
        elif recommendation == "pool_low_sponsor_deposit":
            action["action"] = "advisory_sponsor_deposit"
            action["pool"] = summary.get("pool")
        elif recommendation == "deficit_escalate_purchase":
            action["action"] = "advisory_escalate_purchase"
        else:
            action["action"] = "balanced"

        actions.append(action)

    result = {
        "status": "completed",
        "dry_run": dry_run,
        "ran_at": ran_at,
        "targets": len(targets),
        "actions": actions,
    }
    _last_auto_balance_run = result
    return result
