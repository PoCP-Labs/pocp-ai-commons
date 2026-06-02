"""Nexus-0 autonomous project manager — decompose goals and dispatch Meta Agents."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from meta_agents_spec import META_AGENT_BY_ID, NEXUS_ID
from models.agent_studio import (
    AgentStudioHandoff,
    AgentStudioMission,
    StudioHandoffStatus,
    StudioMissionStatus,
)
from services.agent_studio.handoffs import create_handoff, handoff_to_dict, list_handoffs
from services.agent_studio.mission_plans import MISSION_PLANS, create_mission_from_plan
from services.agent_studio.missions import (
    activate_mission,
    complete_mission,
    create_mission,
    list_missions,
    mission_to_dict,
)
from services.agent_studio.nexus_learning import run_nexus_learning_cycle
from services.agent_studio.outcomes import record_outcome
from services.meta_agent_registry import ensure_meta_agents

NEXUS_PM_MODE = "autonomous_pm"

PROJECT_NORTH_STAR = (
    "Forkable protocol + distributed intelligence + distributed compute — "
    "Phase A local optimization (Exchange Spine, Wallet audit, federation E2E), "
    "then public staging, then Phase B multi-node compute/MCP."
)

# Aligned with docs/ROADMAP-THREE-PHASES.md § Local optimization track
PROJECT_GOALS: list[dict[str, Any]] = [
    {
        "id": "pa_kernel_entity_catalog",
        "priority": 0,
        "phase": "PA-1",
        "title": "Entity catalog — 14 types + capabilities",
        "description": "Register infrastructure entities; seed capability registry; audit_entities --repair green.",
        "owner_agent_id": "pocp-agent-atlas-0",
        "support_agent_ids": ["pocp-agent-pulse-0", "pocp-agent-gauge-0"],
        "exit_signal": "audit_entities.py --repair Complete: True",
        "plan_id": "phase_a_kernel",
    },
    {
        "id": "pa_kernel_invocation_integrity",
        "priority": 0,
        "phase": "PA-2",
        "title": "Invocation ref integrity (PR-A)",
        "description": "invocation_ledger + exchange integrity endpoint; federation step green.",
        "owner_agent_id": "pocp-agent-vault-0",
        "support_agent_ids": ["pocp-agent-gauge-0"],
        "exit_signal": "invocation_ref_integrity acceptance PASS",
        "plan_id": "phase_a_kernel",
    },
    {
        "id": "pa_kernel_settlement_pr_b",
        "priority": 0,
        "phase": "PA-3",
        "title": "Settlement policy + challenge/appeal (PR-B)",
        "description": "contribution_dispute, settlement_policy replay, committed + tested.",
        "owner_agent_id": "pocp-agent-forge-0",
        "support_agent_ids": ["pocp-agent-prism-0", "pocp-agent-gauge-0"],
        "exit_signal": "pytest challenge + settlement_policy green",
        "plan_id": "phase_a_kernel",
    },
    {
        "id": "capability_internet_wave1",
        "priority": 1,
        "phase": "CI",
        "title": "Capability Internet — minimum living network",
        "description": "12-layer protocol reference; NodeProfile + proof chain + federation discover.",
        "owner_agent_id": "pocp-agent-atlas-0",
        "support_agent_ids": ["pocp-agent-pulse-0", "pocp-agent-vault-0", "pocp-agent-gauge-0"],
        "exit_signal": "MINIMUM-LIVING-NETWORK.md checklist green",
        "plan_id": "capability_internet",
    },
    {
        "id": "pa_kernel_federation_acceptance",
        "priority": 0,
        "phase": "PA-4",
        "title": "Federation acceptance full green",
        "description": "run_phase_a_acceptance on :8100/:8101 after backend restart.",
        "owner_agent_id": "pocp-agent-mesh-0",
        "support_agent_ids": ["pocp-agent-gauge-0"],
        "exit_signal": "run_phase_a_acceptance.py --federation all PASS",
        "plan_id": "phase_a_kernel",
    },
    {
        "id": "p0_exchange_spine",
        "priority": 0,
        "phase": "P0",
        "title": "Exchange Spine E2E",
        "description": "Federation exchange demo; exchange proof in acceptance green.",
        "owner_agent_id": "pocp-agent-vault-0",
        "support_agent_ids": ["pocp-agent-mesh-0", "pocp-agent-gauge-0"],
        "exit_signal": "run_phase_a_acceptance.py --federation (exchange proof demo)",
        "plan_id": "phase_a_p0",
    },
    {
        "id": "p0_wallet_audit",
        "priority": 0,
        "phase": "P0",
        "title": "Wallet transaction replay audit",
        "description": "GET /wallets/audit valid; wallet constitution tests green.",
        "owner_agent_id": "pocp-agent-vault-0",
        "support_agent_ids": ["pocp-agent-gauge-0"],
        "exit_signal": "pytest wallet + GET /wallets/audit",
        "plan_id": "phase_a_p0",
    },
    {
        "id": "p1_federation_import",
        "priority": 1,
        "phase": "P1",
        "title": "Federation L1 exchange import",
        "description": "Peer imports exchange proof without silent BC mint.",
        "owner_agent_id": "pocp-agent-mesh-0",
        "support_agent_ids": ["pocp-agent-atlas-0", "pocp-agent-gauge-0"],
        "exit_signal": "federation import tests green",
        "plan_id": "phase_a_full",
    },
    {
        "id": "p1_compute_wire",
        "priority": 1,
        "phase": "P1",
        "title": "Live compute adapter wire",
        "description": "Documented stub→live path; compute tests green.",
        "owner_agent_id": "pocp-agent-grid-0",
        "support_agent_ids": ["pocp-agent-pulse-0", "pocp-agent-gauge-0"],
        "exit_signal": "pytest -k compute",
        "plan_id": "phase_a_full",
    },
    {
        "id": "p2_frontend_demo",
        "priority": 2,
        "phase": "P2",
        "title": "Frontend federation demo UX",
        "description": "ProviderPanel + WalletPanel usable in local federation demo.",
        "owner_agent_id": "pocp-agent-canvas-0",
        "support_agent_ids": ["pocp-agent-herald-0"],
        "exit_signal": "npm run build",
        "plan_id": "phase_a_full",
    },
    {
        "id": "pilot_compliance",
        "priority": 2,
        "phase": "P2",
        "title": "Pilot messaging & NO-TOKEN-FIRST",
        "description": "Public copy safe before staging.",
        "owner_agent_id": "pocp-agent-lex-0",
        "support_agent_ids": ["pocp-agent-compass-0"],
        "exit_signal": "Lex review PASS on README/UI",
        "plan_id": "phase_a_full",
    },
]

PLAN_SEQUENCE: list[str] = ["phase_a_p0", "phase_a_kernel", "phase_a_full"]


def list_project_goals() -> list[dict[str, Any]]:
    return [
        {
            **g,
            "owner_name": META_AGENT_BY_ID.get(g["owner_agent_id"], {}).get("name"),
        }
        for g in PROJECT_GOALS
    ]


def _completed_plan_ids(db: Session) -> set[str]:
    done: set[str] = set()
    for mission in db.query(AgentStudioMission).filter(
        AgentStudioMission.status == StudioMissionStatus.completed
    ):
        plan_id = (mission.metadata_ or {}).get("plan_id")
        if plan_id:
            done.add(plan_id)
    return done


def _next_plan_id(db: Session) -> str | None:
    completed = _completed_plan_ids(db)
    for plan_id in PLAN_SEQUENCE:
        if plan_id not in completed:
            return plan_id
    return None


def _active_mission(db: Session) -> AgentStudioMission | None:
    return (
        db.query(AgentStudioMission)
        .filter(AgentStudioMission.status == StudioMissionStatus.active)
        .order_by(AgentStudioMission.created_at.desc())
        .first()
    )


def _mission_handoffs(db: Session, mission_id: str) -> list[AgentStudioHandoff]:
    return list_handoffs(db, mission_id=mission_id, limit=200)


def _pending_handoffs(handoffs: list[AgentStudioHandoff]) -> list[AgentStudioHandoff]:
    open_status = {StudioHandoffStatus.pending, StudioHandoffStatus.in_progress}
    return [h for h in handoffs if h.status in open_status]


def _dispatch_brief(h: AgentStudioHandoff) -> dict[str, Any]:
    spec = META_AGENT_BY_ID.get(h.to_agent_entity_id, {})
    return {
        "handoff_id": h.id,
        "assignee_entity_id": h.to_agent_entity_id,
        "assignee_name": spec.get("name", h.to_agent_entity_id),
        "task_label": spec.get("task_label"),
        "capabilities": spec.get("capabilities", []),
        "scope": h.scope,
        "tests_run": h.tests_run,
        "status": h.status.value,
        "cursor_skill": f".cursor/skills/pocp-{spec.get('slug', '').replace('-0', '')}/SKILL.md"
        if spec.get("slug")
        else None,
        "prompt_path": f"agents/prompts/{spec.get('slug')}.md" if spec.get("slug") else None,
    }


def _record_nexus_tick(
    db: Session,
    *,
    mission_id: str | None,
    result: str,
    summary: str,
    evidence: dict | None = None,
) -> None:
    record_outcome(
        db,
        agent_entity_id=NEXUS_ID,
        kind="metric",
        result=result,
        mission_id=mission_id,
        summary=summary,
        evidence=evidence or {},
    )


def _spawn_goal_backlog_handoffs(db: Session, mission_id: str) -> list[dict]:
    """After structured plans complete, dispatch one handoff per roadmap goal."""
    existing_scopes = {
        (h.scope or "")[:80]
        for h in db.query(AgentStudioHandoff)
        .filter(AgentStudioHandoff.mission_id == mission_id)
        .all()
    }
    created: list[dict] = []
    for goal in sorted(PROJECT_GOALS, key=lambda g: (g["priority"], g["id"])):
        scope = (
            f"[{goal['phase']}] {goal['title']}: {goal['description']} "
            f"Exit: {goal['exit_signal']}"
        )
        if scope[:80] in existing_scopes:
            continue
        handoff = create_handoff(
            db,
            from_agent_entity_id=NEXUS_ID,
            to_agent_entity_id=goal["owner_agent_id"],
            mission_id=mission_id,
            scope=scope,
            tests_run=goal["exit_signal"],
        )
        created.append(handoff_to_dict(handoff))
        for support_id in goal.get("support_agent_ids") or []:
            support_scope = f"Support {goal['title']}: coordinate with {goal['owner_agent_id']}"
            if support_scope[:80] in existing_scopes:
                continue
            sh = create_handoff(
                db,
                from_agent_entity_id=NEXUS_ID,
                to_agent_entity_id=support_id,
                mission_id=mission_id,
                scope=support_scope,
                tests_run=goal["exit_signal"],
            )
            created.append(handoff_to_dict(sh))
    return created


def nexus_pm_status(db: Session) -> dict[str, Any]:
    ensure_meta_agents(db)
    active = _active_mission(db)
    all_recent = list_missions(db, limit=10)
    pending_all = (
        db.query(AgentStudioHandoff)
        .filter(
            AgentStudioHandoff.status.in_(
                [StudioHandoffStatus.pending, StudioHandoffStatus.in_progress]
            )
        )
        .order_by(AgentStudioHandoff.created_at.desc())
        .limit(30)
        .all()
    )
    return {
        "mode": NEXUS_PM_MODE,
        "orchestrator_entity_id": NEXUS_ID,
        "north_star": PROJECT_NORTH_STAR,
        "goals": list_project_goals(),
        "plan_sequence": PLAN_SEQUENCE,
        "completed_plans": sorted(_completed_plan_ids(db)),
        "next_plan_id": _next_plan_id(db),
        "active_mission": mission_to_dict(active) if active else None,
        "pending_handoff_count": len(pending_all),
        "pending_dispatch": [_dispatch_brief(h) for h in pending_all],
        "recent_missions": [mission_to_dict(m) for m in all_recent],
    }


def run_nexus_autopilot(
    db: Session,
    *,
    sponsor_entity_id: str | None = None,
    force_new_mission: bool = False,
) -> dict[str, Any]:
    """
    One Nexus-0 PM tick: assess roadmap → start/advance missions → dispatch handoffs.

    Idempotent: safe to call on app load and Agent Studio open.
    """
    ensure_meta_agents(db)
    actions: list[dict[str, Any]] = []
    now = datetime.utcnow().isoformat() + "Z"

    active = _active_mission(db)
    learning = run_nexus_learning_cycle(db, mission_id=active.id if active else None)
    actions.append({"type": "learning_cycle", "coached": len(learning.get("agent_coaching", {}).get("candidates", []))})
    if force_new_mission and active is not None:
        forced_id = active.id
        complete_mission(db, forced_id)
        active = None
        actions.append({"type": "mission_force_completed", "mission_id": forced_id})

    if active is None:
        plan_id = _next_plan_id(db)
        if plan_id is not None:
            result = create_mission_from_plan(
                db,
                plan_id,
                sponsor_entity_id=sponsor_entity_id,
                activate=True,
                spawn_handoffs=True,
            )
            mission = db.get(AgentStudioMission, result["mission"]["id"])
            if mission is not None:
                mission.metadata_ = {
                    **(mission.metadata_ or {}),
                    "plan_id": plan_id,
                    "autopilot": True,
                    "nexus_pm": True,
                    "started_at": now,
                }
                db.flush()
            actions.append(
                {
                    "type": "mission_started_from_plan",
                    "plan_id": plan_id,
                    "mission_id": result["mission"]["id"],
                    "handoffs_spawned": result["handoff_count"],
                }
            )
            _record_nexus_tick(
                db,
                mission_id=result["mission"]["id"],
                result="pass",
                summary=f"Nexus-0 started plan {plan_id} with {result['handoff_count']} handoffs.",
                evidence={"plan_id": plan_id, "goals": [g["id"] for g in PROJECT_GOALS if g.get("plan_id") == plan_id]},
            )
            handoffs = _mission_handoffs(db, result["mission"]["id"])
            pending = _pending_handoffs(handoffs)
            return _autopilot_response(
                db,
                mode="dispatched",
                message=f"Nexus-0 launched {plan_id} and assigned {len(pending)} agents.",
                mission_id=result["mission"]["id"],
                actions=actions,
                pending=pending,
                learning_cycle=learning,
            )

        mission = create_mission(
            db,
            title="Continuous improvement — roadmap goals",
            description=PROJECT_NORTH_STAR,
            kind="improve",
            sponsor_entity_id=sponsor_entity_id,
            goal_metrics={"source": "nexus_autopilot", "goals": [g["id"] for g in PROJECT_GOALS]},
        )
        activate_mission(db, mission.id)
        mission.metadata_ = {
            **(mission.metadata_ or {}),
            "plan_id": "continuous",
            "autopilot": True,
            "nexus_pm": True,
            "started_at": now,
        }
        db.flush()
        created = _spawn_goal_backlog_handoffs(db, mission.id)
        actions.append(
            {
                "type": "continuous_mission_started",
                "mission_id": mission.id,
                "handoffs_spawned": len(created),
            }
        )
        _record_nexus_tick(
            db,
            mission_id=mission.id,
            result="pass",
            summary=f"Nexus-0 started continuous track with {len(created)} goal handoffs.",
        )
        handoffs = _mission_handoffs(db, mission.id)
        pending = _pending_handoffs(handoffs)
        return _autopilot_response(
            db,
            mode="dispatched",
            message=f"Nexus-0 dispatched {len(pending)} roadmap goal tasks.",
            mission_id=mission.id,
            actions=actions,
            pending=pending,
            learning_cycle=learning,
        )

    mission = active
    handoffs = _mission_handoffs(db, mission.id)
    pending = _pending_handoffs(handoffs)
    blocked = [h for h in handoffs if h.status == StudioHandoffStatus.blocked]

    if pending:
        actions.append({"type": "monitor", "pending_count": len(pending)})
        _record_nexus_tick(
            db,
            mission_id=mission.id,
            result="partial",
            summary=f"Nexus-0 monitoring {len(pending)} open handoffs.",
            evidence={"pending_ids": [h.id for h in pending[:20]]},
        )
        return _autopilot_response(
            db,
            mode="monitor",
            message="Nexus-0: agents are executing open handoffs.",
            mission_id=mission.id,
            actions=actions,
            pending=pending,
            learning_cycle=learning,
        )

    for bh in blocked:
        unblock = create_handoff(
            db,
            from_agent_entity_id=NEXUS_ID,
            to_agent_entity_id=bh.to_agent_entity_id,
            mission_id=mission.id,
            scope=f"Unblock prior work: {bh.scope or 'handoff'} — report blockers to Nexus.",
            tests_run=bh.tests_run,
            blockers=bh.blockers,
        )
        actions.append(
            {
                "type": "unblock_redispatch",
                "blocked_handoff_id": bh.id,
                "new_handoff_id": unblock.id,
            }
        )

    if blocked:
        db.flush()
        handoffs = _mission_handoffs(db, mission.id)
        pending = _pending_handoffs(handoffs)
        return _autopilot_response(
            db,
            mode="unblock",
            message=f"Nexus-0 re-dispatched {len(blocked)} blocked handoff(s).",
            mission_id=mission.id,
            actions=actions,
            pending=pending,
            learning_cycle=learning,
        )

    complete_mission(db, mission.id)
    actions.append({"type": "mission_completed", "mission_id": mission.id})
    _record_nexus_tick(
        db,
        mission_id=mission.id,
        result="pass",
        summary="Nexus-0 closed mission — all handoffs resolved.",
    )

    next_plan = _next_plan_id(db)
    if next_plan is not None:
        result = create_mission_from_plan(
            db,
            next_plan,
            sponsor_entity_id=sponsor_entity_id,
            activate=True,
            spawn_handoffs=True,
        )
        mission2 = db.get(AgentStudioMission, result["mission"]["id"])
        if mission2 is not None:
            mission2.metadata_ = {
                **(mission2.metadata_ or {}),
                "plan_id": next_plan,
                "autopilot": True,
                "nexus_pm": True,
                "started_at": now,
            }
            db.flush()
        actions.append(
            {
                "type": "next_plan_started",
                "plan_id": next_plan,
                "mission_id": result["mission"]["id"],
                "handoffs_spawned": result["handoff_count"],
            }
        )
        handoffs2 = _mission_handoffs(db, result["mission"]["id"])
        pending2 = _pending_handoffs(handoffs2)
        return _autopilot_response(
            db,
            mode="advanced",
            message=f"Nexus-0 advanced to plan {next_plan} ({len(pending2)} handoffs).",
            mission_id=result["mission"]["id"],
            actions=actions,
            pending=pending2,
            learning_cycle=learning,
        )

    return _autopilot_response(
        db,
        mode="idle",
        message="Nexus-0: all planned tracks complete. Awaiting new goals or force_new_mission.",
        mission_id=None,
        actions=actions,
        pending=[],
        learning_cycle=learning,
    )


def _autopilot_response(
    db: Session,
    *,
    mode: str,
    message: str,
    mission_id: str | None,
    actions: list[dict],
    pending: list[AgentStudioHandoff],
    learning_cycle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lc = learning_cycle or {}
    pr = lc.get("progress_review") or {}
    return {
        "mode": mode,
        "pm_mode": NEXUS_PM_MODE,
        "orchestrator_entity_id": NEXUS_ID,
        "message": message,
        "mission_id": mission_id,
        "actions": actions,
        "pending_handoff_count": len(pending),
        "dispatch_queue": [_dispatch_brief(h) for h in pending],
        "goals": list_project_goals(),
        "learning_cycle": lc,
        "progress_review": pr,
        "completion_percent": pr.get("completion_percent"),
        "coaching_candidates": pr.get("coaching_candidates", []),
        "status": nexus_pm_status(db),
    }
