"""Nexus-0 learning loop — self-study, progress review, Meta Agent coaching."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from meta_agents_spec import META_AGENT_BY_ID, META_AGENT_IDS, NEXUS_ID
from models.agent import Agent
from models.agent_studio import (
    AgentStudioHandoff,
    AgentStudioMission,
    AgentStudioProposal,
    StudioHandoffStatus,
    StudioMissionStatus,
    StudioProposalKind,
    StudioProposalStatus,
)
from services.agent_studio.evolution import (
    apply_proposal,
    get_learning_profile,
    review_proposal,
)
from services.agent_studio.handoffs import create_handoff, handoff_to_dict, list_handoffs
from services.agent_studio.missions import list_missions, mission_to_dict
from services.agent_studio.outcomes import record_outcome
from services.agent_studio.proposals import proposal_to_dict

TRAINING_SCOPE_PREFIX = "[Nexus Training]"
RESEARCH_SCOPE_PREFIX = "[Nexus Research]"
REVIEW_SCOPE_PREFIX = "[Nexus Review]"

# Canonical research corpus for broad PM study (read-only for Nexus)
RESEARCH_CORPUS: list[dict[str, str]] = [
    {"path": "docs/ROADMAP-THREE-PHASES.md", "topic": "phase_priorities"},
    {"path": "docs/ARCHITECTURE.md", "topic": "system_shape"},
    {"path": "docs/protocol/", "topic": "entity_protocol"},
    {"path": "agents/ROSTER.md", "topic": "agent_roles"},
    {"path": "NEURAL-COMMONS-ROADMAP.md", "topic": "neural_commons"},
    {"path": "docs/PILOT-LAUNCH-CHECKLIST.md", "topic": "pilot_exit"},
    {"path": "backend/scripts/run_phase_a_acceptance.py", "topic": "acceptance_gate"},
]

_TRAINING_COOLDOWN_HOURS = 12
_RESEARCH_COOLDOWN_HOURS = 6


def _recent_coaching_proposal(db: Session, agent_entity_id: str, hours: int = 24) -> bool:
    cutoff = _utcnow() - timedelta(hours=hours)
    recent = (
        db.query(AgentStudioProposal)
        .filter(
            AgentStudioProposal.agent_entity_id == agent_entity_id,
            AgentStudioProposal.kind == StudioProposalKind.skill_sync,
            AgentStudioProposal.created_at >= cutoff,
        )
        .first()
    )
    return recent is not None


def _utcnow() -> datetime:
    return datetime.utcnow()


def _nexus_agent(db: Session) -> Agent | None:
    return db.query(Agent).filter(Agent.entity_id == NEXUS_ID).first()


def _update_nexus_profile(db: Session, patch: dict[str, Any]) -> dict[str, Any]:
    agent = _nexus_agent(db)
    if agent is None:
        return {}
    config = dict(agent.config or {})
    profile = dict(config.get("learning_profile") or {})
    for key, value in patch.items():
        if key.endswith("_log") and isinstance(value, list):
            existing = list(profile.get(key) or [])
            profile[key] = (existing + value)[-30:]
        elif isinstance(value, dict) and key in profile and isinstance(profile[key], dict):
            profile[key] = {**profile[key], **value}
        else:
            profile[key] = value
    profile["last_learning_tick"] = _utcnow().isoformat() + "Z"
    config["learning_profile"] = profile
    agent.config = config
    db.flush()
    return profile


def _recent_handoff_exists(
    db: Session,
    *,
    to_agent_entity_id: str,
    scope_prefix: str,
    hours: int,
    mission_id: str | None = None,
) -> bool:
    cutoff = _utcnow() - timedelta(hours=hours)
    q = db.query(AgentStudioHandoff).filter(
        AgentStudioHandoff.to_agent_entity_id == to_agent_entity_id,
        AgentStudioHandoff.created_at >= cutoff,
    )
    if mission_id:
        q = q.filter(AgentStudioHandoff.mission_id == mission_id)
    for h in q.limit(50).all():
        if (h.scope or "").startswith(scope_prefix):
            if h.status in (StudioHandoffStatus.pending, StudioHandoffStatus.in_progress):
                return True
    return False


def review_project_progress(db: Session) -> dict[str, Any]:
    """Nexus-0 progress review — missions, handoffs, goals, agent health."""
    missions = list_missions(db, limit=20)
    all_handoffs = list_handoffs(db, limit=300)

    by_status: dict[str, int] = {}
    for h in all_handoffs:
        by_status[h.status.value] = by_status.get(h.status.value, 0) + 1

    active_missions = [m for m in missions if m.status == StudioMissionStatus.active]
    completed_missions = [m for m in missions if m.status == StudioMissionStatus.completed]

    agent_health: list[dict[str, Any]] = []
    coaching_candidates: list[str] = []
    for eid in sorted(META_AGENT_IDS):
        if eid == NEXUS_ID:
            continue
        try:
            profile = get_learning_profile(db, eid)
        except ValueError:
            continue
        pending_for_agent = sum(
            1
            for h in all_handoffs
            if h.to_agent_entity_id == eid
            and h.status in (StudioHandoffStatus.pending, StudioHandoffStatus.in_progress)
        )
        completed_for_agent = sum(
            1 for h in all_handoffs if h.to_agent_entity_id == eid and h.status == StudioHandoffStatus.completed
        )
        blocked_for_agent = sum(
            1 for h in all_handoffs if h.to_agent_entity_id == eid and h.status == StudioHandoffStatus.blocked
        )
        rate = profile.get("success_rate")
        needs_coaching = (
            pending_for_agent == 0
            and completed_for_agent == 0
            and blocked_for_agent > 0
        ) or (rate is not None and rate < 0.5 and profile.get("outcomes_total", 0) >= 2)
        if needs_coaching:
            coaching_candidates.append(eid)
        spec = META_AGENT_BY_ID.get(eid, {})
        agent_health.append(
            {
                "entity_id": eid,
                "name": spec.get("name"),
                "task_label": spec.get("task_label"),
                "success_rate": rate,
                "outcomes_total": profile.get("outcomes_total", 0),
                "evolution_version": profile.get("evolution_version", 0),
                "pending_handoffs": pending_for_agent,
                "completed_handoffs": completed_for_agent,
                "blocked_handoffs": blocked_for_agent,
                "growth_areas": profile.get("growth_areas", []),
                "needs_coaching": needs_coaching,
            }
        )

    total = len(all_handoffs) or 1
    completion_pct = round(
        100 * by_status.get("completed", 0) / total,
        1,
    )

    return {
        "reviewed_at": _utcnow().isoformat() + "Z",
        "reviewer_entity_id": NEXUS_ID,
        "mission_summary": {
            "active": len(active_missions),
            "completed": len(completed_missions),
            "active_titles": [m.title for m in active_missions[:5]],
        },
        "handoff_summary": by_status,
        "completion_percent": completion_pct,
        "agent_health": agent_health,
        "coaching_candidates": coaching_candidates,
        "research_corpus": RESEARCH_CORPUS,
    }


def nexus_self_study_tick(db: Session, *, mission_id: str | None = None) -> dict[str, Any]:
    """Nexus-0 broad research + records learning outcome; queues Herald doc sync."""
    actions: list[dict[str, Any]] = []
    topics = [c["topic"] for c in RESEARCH_CORPUS]
    summary = (
        f"Nexus-0 research sweep: {len(RESEARCH_CORPUS)} corpus paths "
        f"({', '.join(topics[:4])}…). Align dispatch with ROADMAP + acceptance gate."
    )
    record_outcome(
        db,
        agent_entity_id=NEXUS_ID,
        kind="review",
        result="pass",
        mission_id=mission_id,
        summary=summary,
        evidence={"corpus": RESEARCH_CORPUS, "topics": topics},
    )
    profile = _update_nexus_profile(
        db,
        {
            "research_log": [
                {
                    "at": _utcnow().isoformat() + "Z",
                    "corpus_count": len(RESEARCH_CORPUS),
                    "topics": topics,
                }
            ],
            "pm_skills": {
                "goal_decomposition": True,
                "progress_review": True,
                "agent_coaching": True,
                "broad_research": True,
            },
        },
    )
    actions.append({"type": "nexus_research_outcome", "topics": topics})

    herald_id = "pocp-agent-herald-0"
    if not _recent_handoff_exists(
        db, to_agent_entity_id=herald_id, scope_prefix=RESEARCH_SCOPE_PREFIX, hours=_RESEARCH_COOLDOWN_HOURS
    ):
        handoff = create_handoff(
            db,
            from_agent_entity_id=NEXUS_ID,
            to_agent_entity_id=herald_id,
            mission_id=mission_id,
            scope=(
                f"{RESEARCH_SCOPE_PREFIX} Sync findings from roadmap/protocol review into "
                "docs/ and onboarding — report gaps to Nexus."
            ),
            tests_run="docs review + README consistency",
        )
        actions.append({"type": "research_handoff", "handoff_id": handoff.id, "to": herald_id})

    compass_id = "pocp-agent-compass-0"
    if not _recent_handoff_exists(
        db, to_agent_entity_id=compass_id, scope_prefix=RESEARCH_SCOPE_PREFIX, hours=_RESEARCH_COOLDOWN_HOURS
    ):
        handoff = create_handoff(
            db,
            from_agent_entity_id=NEXUS_ID,
            to_agent_entity_id=compass_id,
            mission_id=mission_id,
            scope=(
                f"{RESEARCH_SCOPE_PREFIX} Reconcile active handoffs vs ROADMAP priorities; "
                "propose priority adjustments to Nexus."
            ),
            tests_run="roadmap cross-check",
        )
        actions.append({"type": "priority_research_handoff", "handoff_id": handoff.id, "to": compass_id})

    return {
        "self_study": True,
        "summary": summary,
        "nexus_profile": profile,
        "actions": actions,
    }


def _create_training_proposal(
    db: Session,
    *,
    agent_entity_id: str,
    mission_id: str | None,
    rationale: str,
    capability_hints: list[str],
) -> AgentStudioProposal:
    proposal = AgentStudioProposal(
        mission_id=mission_id,
        agent_entity_id=agent_entity_id,
        kind=StudioProposalKind.skill_sync,
        status=StudioProposalStatus.pending_review,
        title=f"Nexus coaching: elevate {META_AGENT_BY_ID.get(agent_entity_id, {}).get('name', agent_entity_id)}",
        rationale=rationale,
        proposed_changes={
            "action": "grow",
            "coach_entity_id": NEXUS_ID,
            "capability_hints": capability_hints,
            "training_modules": [
                "re-read agents/prompts/{slug}.md",
                "run domain pytest from handoff tests_run",
                "update learning_profile strengths after pass",
            ],
        },
        source_outcome_ids=[],
    )
    db.add(proposal)
    db.flush()
    return proposal


def _auto_apply_training_proposal(db: Session, proposal: AgentStudioProposal) -> dict[str, Any] | None:
    """Nexus approves and applies skill-sync coaching proposals (playbook patch file)."""
    review_proposal(
        db,
        proposal.id,
        approve=True,
        reviewer_entity_id=NEXUS_ID,
        review_note="Auto-approved Nexus coaching cycle",
    )
    try:
        return apply_proposal(db, proposal.id, actor_entity_id=NEXUS_ID)
    except ValueError:
        return None


def train_meta_agents_tick(
    db: Session,
    progress: dict[str, Any],
    *,
    mission_id: str | None = None,
) -> dict[str, Any]:
    """Nexus-0 coaches Meta Agents — training handoffs + skill proposals."""
    actions: list[dict[str, Any]] = []
    proposals_created: list[dict] = []
    training_handoffs: list[dict] = []

    candidates = list(progress.get("coaching_candidates") or [])

    for agent_entity_id in candidates[:8]:
        if agent_entity_id == NEXUS_ID:
            continue
        spec = META_AGENT_BY_ID.get(agent_entity_id, {})
        slug = spec.get("slug", "")
        caps = list(spec.get("capabilities") or [])

        if not _recent_handoff_exists(
            db,
            to_agent_entity_id=agent_entity_id,
            scope_prefix=TRAINING_SCOPE_PREFIX,
            hours=_TRAINING_COOLDOWN_HOURS,
            mission_id=mission_id,
        ):
            handoff = create_handoff(
                db,
                from_agent_entity_id=NEXUS_ID,
                to_agent_entity_id=agent_entity_id,
                mission_id=mission_id,
                scope=(
                    f"{TRAINING_SCOPE_PREFIX} Coach cycle: study agents/prompts/{slug}.md, "
                    f"run roster tests, report blockers + skill gaps to Nexus. "
                    f"Focus capabilities: {', '.join(caps[:4])}."
                ),
                tests_run=spec.get("task_label", "domain tests"),
            )
            training_handoffs.append(handoff_to_dict(handoff))
            actions.append({"type": "training_handoff", "to": agent_entity_id, "handoff_id": handoff.id})

        health = _health_row(progress, agent_entity_id)
        rationale = (
            f"Nexus-0 coaching: strengthen {spec.get('name')} based on progress review "
            f"(success_rate={health.get('success_rate') if health else 'n/a'})."
        )
        if not _recent_coaching_proposal(db, agent_entity_id):
            proposal = _create_training_proposal(
                db,
                agent_entity_id=agent_entity_id,
                mission_id=mission_id,
                rationale=rationale,
                capability_hints=caps[:3],
            )
            applied = _auto_apply_training_proposal(db, proposal)
            proposals_created.append(proposal_to_dict(proposal))
            actions.append(
                {
                    "type": "training_proposal",
                    "proposal_id": proposal.id,
                    "agent_entity_id": agent_entity_id,
                    "applied": applied is not None,
                }
            )

    for row in progress.get("agent_health") or []:
        agent_entity_id = row["entity_id"]
        if agent_entity_id == NEXUS_ID or row.get("pending_handoffs", 0) == 0:
            continue
        if _recent_handoff_exists(
            db,
            to_agent_entity_id=agent_entity_id,
            scope_prefix=REVIEW_SCOPE_PREFIX,
            hours=_TRAINING_COOLDOWN_HOURS,
        ):
            continue
        spec = META_AGENT_BY_ID.get(agent_entity_id, {})
        handoff = create_handoff(
            db,
            from_agent_entity_id=NEXUS_ID,
            to_agent_entity_id=agent_entity_id,
            mission_id=mission_id,
            scope=(
                f"{REVIEW_SCOPE_PREFIX} Status check: confirm your open handoffs, "
                "report completion % and blockers to Nexus within one cycle."
            ),
            tests_run="handoff status report",
        )
        training_handoffs.append(handoff_to_dict(handoff))
        actions.append({"type": "completion_review", "to": agent_entity_id})

    _update_nexus_profile(
        db,
        {
            "coaching_log": [
                {
                    "at": _utcnow().isoformat() + "Z",
                    "trained": len(candidates),
                    "proposals": len(proposals_created),
                }
            ],
            "pm_reviews": [{"at": _utcnow().isoformat() + "Z", "completion_pct": progress.get("completion_percent")}],
        },
    )

    record_outcome(
        db,
        agent_entity_id=NEXUS_ID,
        kind="metric",
        result="pass",
        mission_id=mission_id,
        summary=f"Nexus-0 coached {len(candidates)} agents; {len(training_handoffs)} training/review handoffs.",
        evidence={"candidates": candidates, "proposals": len(proposals_created)},
    )

    return {
        "coaching": True,
        "candidates": candidates,
        "training_handoffs": training_handoffs,
        "proposals": proposals_created,
        "actions": actions,
    }


def _health_row(progress: dict, entity_id: str) -> dict | None:
    for row in progress.get("agent_health") or []:
        if row.get("entity_id") == entity_id:
            return row
    return None


def run_nexus_learning_cycle(
    db: Session,
    *,
    mission_id: str | None = None,
) -> dict[str, Any]:
    """Full Nexus learning tick: review → self-study → coach agents."""
    progress = review_project_progress(db)
    self_study = nexus_self_study_tick(db, mission_id=mission_id)
    coaching = train_meta_agents_tick(db, progress, mission_id=mission_id)
    return {
        "learning_cycle": True,
        "progress_review": progress,
        "self_study": self_study,
        "agent_coaching": coaching,
    }


def nexus_learning_status(db: Session) -> dict[str, Any]:
    agent = _nexus_agent(db)
    profile = (agent.config or {}).get("learning_profile", {}) if agent else {}
    return {
        "orchestrator_entity_id": NEXUS_ID,
        "learning_profile": profile,
        "research_corpus": RESEARCH_CORPUS,
        "progress_snapshot": review_project_progress(db),
    }
