"""
Nexus-0 super-automation — full PDCA without human in the loop.

Plan  → Nexus autopilot (roadmap, missions, handoffs)
Do    → Cursor executes pending Meta Agent handoffs
Check → Optional acceptance probe + progress review
Act   → Nexus learning cycle (coach, proposals, self-study)
Heal  → Platform health failures dispatch Gauge/Sentinel repair handoffs
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from meta_agents_spec import NEXUS_ID
from services.agent_studio.cursor_automation import (
    automation_enabled,
    count_pending_for_cursor,
    run_cursor_automation_tick,
)
from services.agent_studio.handoffs import create_handoff
from services.agent_studio.nexus_autopilot import run_nexus_autopilot
from services.agent_studio.nexus_learning import run_nexus_learning_cycle
from services.agent_studio.platform_health import probe_platform
from services.meta_agent_registry import ensure_meta_agents

_REPO = Path(__file__).resolve().parents[3]
_GAUGE_ID = "pocp-agent-gauge-0"
_SENTINEL_ID = "pocp-agent-sentinel-0"

_LAST_SUPER_TICK: dict[str, Any] = {}


def super_loop_enabled() -> bool:
    return os.getenv("POCP_NEXUS_SUPER_LOOP", "false").lower() in ("1", "true", "yes")


def super_loop_host_mode() -> bool:
    """When true, automation runs on the Windows/Linux host — not inside Docker backend."""
    return os.getenv("POCP_NEXUS_SUPER_LOOP_HOST", "false").lower() in ("1", "true", "yes")


def super_loop_backend_enabled() -> bool:
    """In-process super-loop inside uvicorn (disabled when host worker owns the loop)."""
    if super_loop_host_mode():
        return False
    return super_loop_enabled()


def cursor_backend_automation_enabled() -> bool:
    """Cursor-only background loop in uvicorn (off when super-loop or host mode is active)."""
    if super_loop_host_mode() or super_loop_backend_enabled():
        return False
    return os.getenv("POCP_CURSOR_AUTOMATION", "false").lower() in ("1", "true", "yes")


def _max_cursor_per_tick() -> int:
    try:
        return max(0, int(os.getenv("POCP_SUPER_LOOP_MAX_CURSOR_PER_TICK", "2")))
    except ValueError:
        return 2


def _run_acceptance_probe() -> dict[str, Any]:
    if os.getenv("POCP_SUPER_LOOP_RUN_ACCEPTANCE", "false").lower() not in ("1", "true", "yes"):
        return {"ran": False, "reason": "POCP_SUPER_LOOP_RUN_ACCEPTANCE not enabled"}
    script = _REPO / "backend" / "scripts" / "run_phase_a_acceptance.py"
    if not script.is_file():
        return {"ran": False, "reason": "acceptance script missing"}
    base = os.getenv("BACKEND_URL", "http://127.0.0.1:8008")
    try:
        proc = subprocess.run(
            [sys.executable, str(script), base],
            cwd=str(_REPO),
            capture_output=True,
            text=True,
            timeout=int(os.getenv("POCP_SUPER_LOOP_ACCEPTANCE_TIMEOUT_SEC", "600")),
        )
        return {
            "ran": True,
            "exit_code": proc.returncode,
            "ok": proc.returncode == 0,
            "stdout_tail": (proc.stdout or "")[-2000:],
            "stderr_tail": (proc.stderr or "")[-1000:],
        }
    except Exception as exc:
        return {"ran": True, "ok": False, "error": str(exc)[:500]}


def _dispatch_platform_repair(db: Session, *, mission_id: str | None, health: dict[str, Any]) -> list[dict[str, Any]]:
    if health.get("ok"):
        return []
    issues = "; ".join(health.get("issues") or [])[:1500]
    created: list[dict[str, Any]] = []
    for agent_id, label in ((_GAUGE_ID, "qa_repair"), (_SENTINEL_ID, "security_repair")):
        h = create_handoff(
            db,
            from_agent_entity_id=NEXUS_ID,
            to_agent_entity_id=agent_id,
            mission_id=mission_id,
            scope=(
                f"[Nexus Platform Repair] PoCP health check failed ({label}). "
                f"Diagnose and fix: {issues}. Run tests, commit fixes within roster paths."
            ),
            tests_run="health_check.py + domain pytest",
        )
        created.append({"handoff_id": h.id, "assignee": agent_id, "label": label})
    return created


def _dispatch_acceptance_review(db: Session, *, mission_id: str | None, acceptance: dict[str, Any]) -> dict[str, Any] | None:
    if not acceptance.get("ran") or acceptance.get("ok"):
        return None
    h = create_handoff(
        db,
        from_agent_entity_id=NEXUS_ID,
        to_agent_entity_id=_GAUGE_ID,
        mission_id=mission_id,
        scope=(
            "[Nexus Check] Phase A acceptance failed. Triage failures, fix tests or docs, "
            "re-run run_phase_a_acceptance.py until green."
        ),
        tests_run="run_phase_a_acceptance.py",
    )
    return {"handoff_id": h.id, "assignee": _GAUGE_ID}


def run_nexus_super_tick(
    db: Session,
    *,
    sponsor_entity_id: str | None = None,
    force_new_mission: bool = False,
    max_cursor_handoffs: int | None = None,
) -> dict[str, Any]:
    """
    One full super-automation cycle (human-out-of-loop target).

    Safe to run on a timer: idempotent Nexus PM + bounded Cursor executions.
    """
    global _LAST_SUPER_TICK
    ensure_meta_agents(db)
    limit = max_cursor_handoffs if max_cursor_handoffs is not None else _max_cursor_per_tick()
    steps: list[dict[str, Any]] = []

    health = probe_platform(db)
    steps.append({"phase": "probe", "health": health})

    nexus = run_nexus_autopilot(
        db,
        sponsor_entity_id=sponsor_entity_id,
        force_new_mission=force_new_mission,
    )
    mission_id = nexus.get("mission_id")
    steps.append(
        {
            "phase": "plan_dispatch",
            "mode": nexus.get("mode"),
            "message": nexus.get("message"),
            "pending_after_plan": nexus.get("pending_handoff_count"),
            "actions": nexus.get("actions"),
        }
    )

    cursor_processed: list[dict[str, Any]] = []
    cursor_errors: list[str] = []
    if automation_enabled() and limit > 0:
        for i in range(limit):
            pending = count_pending_for_cursor(db)
            if pending < 1:
                steps.append({"phase": "do_cursor", "iteration": i, "skipped": "no pending handoffs"})
                break
            try:
                tick = run_cursor_automation_tick(db, max_handoffs=1, verbose=False)
                cursor_processed.extend(tick.get("processed") or [])
                cursor_errors.extend(tick.get("errors") or [])
                steps.append(
                    {
                        "phase": "do_cursor",
                        "iteration": i,
                        "picked": tick.get("picked"),
                        "processed": tick.get("processed"),
                        "errors": tick.get("errors"),
                    }
                )
            except Exception as exc:
                cursor_errors.append(str(exc))
                steps.append({"phase": "do_cursor", "iteration": i, "error": str(exc)})
                break
    else:
        steps.append(
            {
                "phase": "do_cursor",
                "skipped": True,
                "reason": "cursor automation not active" if not automation_enabled() else "limit=0",
            }
        )

    acceptance = _run_acceptance_probe()
    steps.append({"phase": "check_acceptance", **acceptance})
    acceptance_handoff = _dispatch_acceptance_review(db, mission_id=mission_id, acceptance=acceptance)
    if acceptance_handoff:
        steps.append({"phase": "check_acceptance_dispatch", **acceptance_handoff})

    learning = run_nexus_learning_cycle(db, mission_id=mission_id)
    steps.append(
        {
            "phase": "act_pdca",
            "completion_percent": (learning.get("progress_review") or {}).get("completion_percent"),
            "coached": len((learning.get("agent_coaching") or {}).get("candidates") or []),
        }
    )

    evolution: dict[str, Any] = {"skipped": True}
    try:
        from services.agent_studio.auto_evolution import run_auto_evolution_tick

        evolution = run_auto_evolution_tick(db)
        steps.append({"phase": "evolve_memory", **evolution})
    except Exception as exc:
        steps.append({"phase": "evolve_memory", "error": str(exc)[:300]})

    repair_handoffs = _dispatch_platform_repair(db, mission_id=mission_id, health=health)
    if repair_handoffs:
        steps.append({"phase": "heal_platform", "handoffs": repair_handoffs})

    pending_after = count_pending_for_cursor(db)
    payload = {
        "ran": True,
        "at": datetime.utcnow().isoformat() + "Z",
        "super_loop": True,
        "enabled_flag": os.getenv("POCP_NEXUS_SUPER_LOOP", "false"),
        "platform_healthy": health.get("ok"),
        "health": health,
        "nexus": {
            "mode": nexus.get("mode"),
            "message": nexus.get("message"),
            "mission_id": mission_id,
            "pending_handoff_count": pending_after,
        },
        "cursor": {
            "automation_active": automation_enabled(),
            "processed_count": len(cursor_processed),
            "processed": cursor_processed,
            "errors": cursor_errors,
        },
        "acceptance": acceptance,
        "learning_cycle": learning,
        "steps": steps,
        "pending_for_cursor": pending_after,
        "human_required": bool(
            cursor_errors
            or not health.get("ok")
            or (acceptance.get("ran") and not acceptance.get("ok"))
        ),
        "human_required_reasons": _human_required_reasons(health, cursor_errors, acceptance),
    }
    _LAST_SUPER_TICK = payload
    return payload


def _human_required_reasons(
    health: dict[str, Any],
    cursor_errors: list[str],
    acceptance: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if not health.get("ok"):
        reasons.append("platform health failed — repair handoffs dispatched")
    if cursor_errors:
        reasons.append(f"cursor errors: {'; '.join(cursor_errors[:3])}")
    if acceptance.get("ran") and not acceptance.get("ok"):
        reasons.append("phase A acceptance failed — Gauge handoff dispatched")
    if not reasons:
        reasons.append("none — loop can continue autonomously")
    return reasons


def last_super_tick() -> dict[str, Any]:
    return dict(_LAST_SUPER_TICK)


def super_loop_status() -> dict[str, Any]:
    host = super_loop_host_mode()
    backend = super_loop_backend_enabled()
    return {
        "enabled": super_loop_enabled() or host,
        "host_mode": host,
        "backend_loop_active": backend,
        "interval_sec": int(os.getenv("POCP_NEXUS_SUPER_LOOP_INTERVAL_SEC", "600")),
        "max_cursor_per_tick": _max_cursor_per_tick(),
        "run_acceptance": os.getenv("POCP_SUPER_LOOP_RUN_ACCEPTANCE", "false"),
        "cursor_automation": os.getenv("POCP_CURSOR_AUTOMATION", "false"),
        "nexus_autopilot": os.getenv("POCP_NEXUS_AUTOPILOT", "true"),
        "repo_root": os.getenv("POCP_REPO_ROOT", ""),
        "backend_url": os.getenv("BACKEND_URL", "http://127.0.0.1:8008"),
        "deployment_hint": (
            "Run .\\scripts\\run-studio-super-loop.ps1 on the Windows host (recommended)."
            if host
            else (
                "Docker backend runs super-loop when POCP_NEXUS_SUPER_LOOP=true."
                if backend
                else "Enable POCP_NEXUS_SUPER_LOOP_HOST=true + host worker, or POCP_NEXUS_SUPER_LOOP=true in backend."
            )
        ),
        "last_tick": last_super_tick(),
    }
