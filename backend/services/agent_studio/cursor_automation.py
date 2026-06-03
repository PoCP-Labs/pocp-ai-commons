"""Agent Studio ↔ Cursor — pick pending handoffs and run them automatically."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from meta_agents_spec import NEXUS_ID
from models.agent_studio import AgentStudioHandoff, StudioHandoffStatus
from services.agent_studio.cursor_bridge import (
    automation_enabled,
    automation_status,
    build_handoff_prompt,
    execute_handoff_prompt,
)
from services.agent_studio.handoffs import complete_handoff
from services.agent_studio.outcomes import record_outcome

# In-memory last tick (process-local; sufficient for single worker)
_LAST_TICK: dict[str, Any] = {}


def _max_per_tick() -> int:
    try:
        return max(1, int(os.getenv("POCP_CURSOR_AUTOMATION_MAX_PER_TICK", "1")))
    except ValueError:
        return 1


_CI_SCOPE_TOKENS = (
    "[ci-",
    "[ci gate]",
    "capability internet",
    "protocol economy",
    "minimum living network",
)


def _is_ci_scope(scope: str | None) -> bool:
    text = (scope or "").lower()
    return any(token in text for token in _CI_SCOPE_TOKENS)


def _ci_only_pick() -> bool:
    return os.getenv("POCP_CURSOR_CI_ONLY", "true").lower() in ("1", "true", "yes")


def _cursor_assignable(handoff: AgentStudioHandoff) -> bool:
    """Nexus-0 is excluded except CI gate closure (Gauge → Nexus)."""
    if handoff.to_agent_entity_id != NEXUS_ID:
        return True
    return "[ci gate]" in (handoff.scope or "").lower()


def pick_pending_handoffs(db: Session, *, limit: int = 5) -> list[AgentStudioHandoff]:
    """Handoffs assignable to Cursor — CI protocol work first; optional CI-only mode."""
    rows = (
        db.query(AgentStudioHandoff)
        .filter(AgentStudioHandoff.status == StudioHandoffStatus.pending)
        .order_by(AgentStudioHandoff.created_at.asc())
        .all()
    )
    rows = [h for h in rows if _cursor_assignable(h)]
    ci_rows = [h for h in rows if _is_ci_scope(h.scope)]
    if ci_rows:
        return ci_rows[:limit]
    if _ci_only_pick():
        return []
    other_rows = [h for h in rows if h not in ci_rows]
    return other_rows[:limit]


def _mark_in_progress(db: Session, handoff: AgentStudioHandoff) -> None:
    handoff.status = StudioHandoffStatus.in_progress
    meta = dict(handoff.metadata_ or {})
    meta["cursor_started_at"] = datetime.utcnow().isoformat() + "Z"
    handoff.metadata_ = meta
    db.flush()


def run_handoff_with_cursor(
    db: Session, handoff: AgentStudioHandoff, *, verbose: bool = False
) -> dict[str, Any]:
    """Execute one handoff through Cursor SDK and update Studio records."""
    from meta_agents_spec import META_AGENT_BY_ID
    from services.agent_studio.studio_console import log_block, log_step

    spec = META_AGENT_BY_ID.get(handoff.to_agent_entity_id, {})
    if verbose:
        log_step(
            "Handoff picked",
            f"id={handoff.id}\n"
            f"assignee={spec.get('name', handoff.to_agent_entity_id)}\n"
            f"scope={(handoff.scope or '')[:200]}",
        )

    _mark_in_progress(db, handoff)
    if verbose:
        log_step("Handoff status -> in_progress")

    memory_context = None
    try:
        from services.agent_studio.memory_store import format_memory_context

        memory_context = format_memory_context(db, handoff.to_agent_entity_id, limit=6)
    except Exception:
        pass
    prompt = build_handoff_prompt(
        handoff_id=handoff.id,
        to_agent_entity_id=handoff.to_agent_entity_id,
        scope=handoff.scope,
        tests_run=handoff.tests_run,
        mission_id=handoff.mission_id,
        memory_context=memory_context,
    )
    if verbose:
        log_step("Calling Cursor SDK (this may take several minutes)...")

    exec_result = execute_handoff_prompt(prompt, verbose=verbose)
    meta = dict(handoff.metadata_ or {})
    meta["cursor_execution"] = exec_result
    handoff.metadata_ = meta

    if exec_result.get("startup_error"):
        complete_handoff(
            db,
            handoff.id,
            status="blocked",
            blockers=exec_result.get("message", "Cursor startup failed"),
        )
        record_outcome(
            db,
            agent_entity_id=handoff.to_agent_entity_id,
            kind="test",
            result="fail",
            mission_id=handoff.mission_id,
            handoff_id=handoff.id,
            summary=f"Cursor startup failed: {exec_result.get('message', '')[:500]}",
            evidence=exec_result,
        )
        return {"handoff_id": handoff.id, "status": "blocked", "cursor": exec_result}

    if exec_result.get("ok"):
        complete_handoff(db, handoff.id, status="completed")
        record_outcome(
            db,
            agent_entity_id=handoff.to_agent_entity_id,
            kind="test",
            result="pass",
            mission_id=handoff.mission_id,
            handoff_id=handoff.id,
            summary=(exec_result.get("summary") or "Cursor run finished")[:2000],
            evidence={"run_id": exec_result.get("run_id"), "agent_id": exec_result.get("agent_id")},
        )
        return {"handoff_id": handoff.id, "status": "completed", "cursor": exec_result}

    complete_handoff(
        db,
        handoff.id,
        status="blocked",
        blockers=(exec_result.get("summary") or exec_result.get("status") or "Cursor run failed")[:2000],
    )
    record_outcome(
        db,
        agent_entity_id=handoff.to_agent_entity_id,
        kind="test",
        result="fail",
        mission_id=handoff.mission_id,
        handoff_id=handoff.id,
        summary=f"Cursor run status={exec_result.get('status')}",
        evidence=exec_result,
    )
    return {"handoff_id": handoff.id, "status": "blocked", "cursor": exec_result}


def run_cursor_automation_tick(
    db: Session, *, max_handoffs: int | None = None, verbose: bool = False
) -> dict[str, Any]:
    """Process up to N pending handoffs via Cursor."""
    global _LAST_TICK
    limit = max_handoffs if max_handoffs is not None else _max_per_tick()
    status = automation_status()

    if not automation_enabled():
        payload = {
            "ran": False,
            "reason": "automation not active",
            "status": status,
            "processed": [],
        }
        _LAST_TICK = payload
        return payload

    pending = pick_pending_handoffs(db, limit=limit)
    processed: list[dict[str, Any]] = []
    errors: list[str] = []

    if verbose:
        from services.agent_studio.studio_console import log_step

        log_step(f"Queue: {len(pending)} handoff(s) eligible (processing up to {limit})")

    for handoff in pending[:limit]:
        try:
            processed.append(run_handoff_with_cursor(db, handoff, verbose=verbose))
        except Exception as exc:
            db.rollback()
            errors.append(f"{handoff.id}: {exc}")
            try:
                complete_handoff(db, handoff.id, status="blocked", blockers=str(exc)[:500])
                db.flush()
            except Exception:
                db.rollback()

    nexus_followup = None
    skip_nexus = os.getenv("POCP_CURSOR_SKIP_NEXUS_FOLLOWUP", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    if processed and not skip_nexus:
        from services.agent_studio.nexus_autopilot import run_nexus_autopilot

        try:
            nexus_followup = run_nexus_autopilot(db)
        except Exception as exc:
            db.rollback()
            errors.append(f"nexus follow-up: {exc}")

    payload = {
        "ran": True,
        "at": datetime.utcnow().isoformat() + "Z",
        "status": status,
        "picked": len(pending),
        "processed": processed,
        "errors": errors,
        "nexus_followup_mode": (nexus_followup or {}).get("mode") if nexus_followup else None,
    }
    _LAST_TICK = payload
    return payload


def last_automation_tick() -> dict[str, Any]:
    return dict(_LAST_TICK)


def count_pending_for_cursor(db: Session) -> int:
    return (
        db.query(AgentStudioHandoff)
        .filter(
            AgentStudioHandoff.status == StudioHandoffStatus.pending,
            AgentStudioHandoff.to_agent_entity_id != NEXUS_ID,
        )
        .count()
    )
