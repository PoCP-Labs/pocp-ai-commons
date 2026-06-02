"""O.E.R. evolution loop — Observe, Evaluate, Refine (learn / grow / transform / improve)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from meta_agents_spec import META_AGENT_IDS, NEXUS_ID
from models.agent import Agent
from models.agent_studio import (
    AgentStudioMission,
    AgentStudioOutcome,
    AgentStudioProposal,
    StudioMissionStatus,
    StudioOutcomeResult,
    StudioProposalKind,
    StudioProposalStatus,
)
from services.agent_studio.missions import list_missions, mission_to_dict
from services.agent_studio.handoffs import handoff_to_dict, list_handoffs
from services.agent_studio.outcomes import outcome_to_dict
from services.agent_studio.proposals import list_proposals, proposal_to_dict
from services.agent_studio.agent_capabilities import get_agent_capabilities
from services.agent_studio.memory_store import memory_count, vault_summary
from services.meta_agent_registry import ensure_meta_agents, list_meta_agents


def _outcome_result_value(result: StudioOutcomeResult) -> str:
    v = result.value
    return "pass" if v == "pass_" else v


def get_learning_profile(db: Session, agent_entity_id: str) -> dict:
    if agent_entity_id not in META_AGENT_IDS:
        raise ValueError("Not a Meta Agent")

    outcomes = (
        db.query(AgentStudioOutcome)
        .filter(AgentStudioOutcome.agent_entity_id == agent_entity_id)
        .order_by(AgentStudioOutcome.created_at.desc())
        .limit(100)
        .all()
    )
    total = len(outcomes)
    passes = sum(1 for o in outcomes if o.result == StudioOutcomeResult.pass_)
    fails = sum(1 for o in outcomes if o.result == StudioOutcomeResult.fail)

    agent = db.query(Agent).filter(Agent.entity_id == agent_entity_id).first()
    stored = (agent.config or {}).get("learning_profile") if agent else {}
    if not isinstance(stored, dict):
        stored = {}

    applied_proposals = (
        db.query(AgentStudioProposal)
        .filter(
            AgentStudioProposal.agent_entity_id == agent_entity_id,
            AgentStudioProposal.status == StudioProposalStatus.applied,
        )
        .count()
    )

    caps = get_agent_capabilities(db, agent_entity_id)
    return {
        "agent_entity_id": agent_entity_id,
        "outcomes_total": total,
        "success_rate": round(passes / total, 3) if total else None,
        "pass_count": passes,
        "fail_count": fails,
        "applied_proposals": applied_proposals,
        "evolution_version": stored.get("evolution_version", 0),
        "strengths": stored.get("strengths", []),
        "growth_areas": stored.get("growth_areas", []),
        "evolved_capabilities": caps.get("evolved_capabilities", []),
        "effective_capabilities": caps.get("effective_capabilities", []),
        "memory_count": memory_count(db, agent_entity_id),
        "memory_store_path": stored.get("memory_store_path"),
        "recent_outcomes": [outcome_to_dict(o) for o in outcomes[:5]],
    }


def process_outcome(db: Session, outcome_id: str) -> AgentStudioProposal | None:
    """Evaluate an outcome and auto-generate improvement proposal when warranted."""
    outcome = db.get(AgentStudioOutcome, outcome_id)
    if outcome is None:
        raise ValueError("Outcome not found")

    if outcome.result == StudioOutcomeResult.pass_:
        return _maybe_growth_proposal(db, outcome)

    return _failure_improvement_proposal(db, outcome)


def _failure_improvement_proposal(
    db: Session, outcome: AgentStudioOutcome
) -> AgentStudioProposal:
    kind_map = {
        "test": StudioProposalKind.prompt_refine,
        "acceptance": StudioProposalKind.workflow_update,
        "review": StudioProposalKind.config_tune,
    }
    proposal = AgentStudioProposal(
        mission_id=outcome.mission_id,
        agent_entity_id=outcome.agent_entity_id,
        kind=kind_map.get(outcome.kind.value, StudioProposalKind.config_tune),
        status=StudioProposalStatus.pending_review,
        title=f"Improve after {_outcome_result_value(outcome.result)}: {outcome.kind.value}",
        rationale=outcome.summary or "Auto-generated from failed outcome — refine agent playbook.",
        proposed_changes={
            "action": "improve",
            "suggested_reviewers": ["pocp-agent-gauge-0", "pocp-agent-atlas-0"],
            "evidence": outcome.evidence or {},
        },
        source_outcome_ids=[outcome.id],
    )
    db.add(proposal)
    db.flush()
    return proposal


def _maybe_growth_proposal(
    db: Session, outcome: AgentStudioOutcome
) -> AgentStudioProposal | None:
    recent_passes = (
        db.query(AgentStudioOutcome)
        .filter(
            AgentStudioOutcome.agent_entity_id == outcome.agent_entity_id,
            AgentStudioOutcome.result == StudioOutcomeResult.pass_,
            AgentStudioOutcome.kind == outcome.kind,
        )
        .count()
    )
    if recent_passes < 3:
        return None

    proposal = AgentStudioProposal(
        mission_id=outcome.mission_id,
        agent_entity_id=outcome.agent_entity_id,
        kind=StudioProposalKind.capability_add,
        status=StudioProposalStatus.pending_review,
        title=f"Grow: expand {outcome.kind.value} mastery",
        rationale=(
            f"Agent recorded {recent_passes} consecutive passes for {outcome.kind.value}. "
            "Propose capability elevation or broader writable scope (Atlas review)."
        ),
        proposed_changes={
            "action": "grow",
            "capability_hint": outcome.kind.value,
            "pass_streak": recent_passes,
        },
        source_outcome_ids=[outcome.id],
    )
    db.add(proposal)
    db.flush()
    return proposal


def review_proposal(
    db: Session,
    proposal_id: str,
    *,
    approve: bool,
    reviewer_entity_id: str,
    review_note: str | None = None,
) -> AgentStudioProposal:
    proposal = db.get(AgentStudioProposal, proposal_id)
    if proposal is None:
        raise ValueError("Proposal not found")
    proposal.status = (
        StudioProposalStatus.approved if approve else StudioProposalStatus.rejected
    )
    proposal.reviewer_entity_id = reviewer_entity_id
    proposal.review_note = review_note
    proposal.reviewed_at = datetime.utcnow()
    db.flush()
    return proposal


def apply_proposal(db: Session, proposal_id: str, *, actor_entity_id: str) -> dict:
    """Apply approved proposal to Agent learning profile (self-improvement without auto git write)."""
    proposal = db.get(AgentStudioProposal, proposal_id)
    if proposal is None:
        raise ValueError("Proposal not found")
    if proposal.status != StudioProposalStatus.approved:
        raise ValueError("Proposal must be approved before apply")

    agent = db.query(Agent).filter(Agent.entity_id == proposal.agent_entity_id).first()
    if agent is None:
        raise ValueError("Agent row missing")

    config = dict(agent.config or {})
    profile = dict(config.get("learning_profile") or {})
    profile["evolution_version"] = int(profile.get("evolution_version", 0)) + 1
    profile["last_applied_proposal_id"] = proposal.id
    profile["last_applied_at"] = datetime.utcnow().isoformat()
    profile["last_applied_by"] = actor_entity_id

    changes = proposal.proposed_changes or {}
    action = changes.get("action")
    if action == "grow":
        strengths = list(profile.get("strengths") or [])
        hint = changes.get("capability_hint")
        if hint and hint not in strengths:
            strengths.append(hint)
        for extra in changes.get("capability_hints") or []:
            if extra and extra not in strengths:
                strengths.append(extra)
        if changes.get("coach_entity_id"):
            coaches = list(profile.get("coached_by_nexus") or [])
            if changes["coach_entity_id"] not in coaches:
                coaches.append(changes["coach_entity_id"])
            profile["coached_by_nexus"] = coaches[-5:]
        profile["strengths"] = strengths[-10:]
    elif action == "improve":
        growth = list(profile.get("growth_areas") or [])
        area = proposal.kind.value
        if area not in growth:
            growth.append(area)
        profile["growth_areas"] = growth[-10:]

    profile["applied_history"] = (list(profile.get("applied_history") or []) + [
        {"proposal_id": proposal.id, "title": proposal.title, "at": datetime.utcnow().isoformat()}
    ])[-20:]

    config["learning_profile"] = profile
    agent.config = config

    proposal.status = StudioProposalStatus.applied
    proposal.applied_at = datetime.utcnow()
    proposal.metadata_ = {
        **(proposal.metadata_ or {}),
        "applied_by": actor_entity_id,
    }

    from services.agent_studio.patch_suggestions import write_patch_suggestion_file

    patch_info = write_patch_suggestion_file(
        proposal,
        agent,
        actor_entity_id=actor_entity_id,
        evolution_version=profile["evolution_version"],
    )
    profile["last_patch_file"] = patch_info["patch_file"]
    config["learning_profile"] = profile
    agent.config = config
    proposal.metadata_["patch_file"] = patch_info["patch_file"]

    db.flush()

    return {
        "proposal_id": proposal.id,
        "agent_entity_id": proposal.agent_entity_id,
        "evolution_version": profile["evolution_version"],
        "learning_profile": profile,
        "patch_suggestion": patch_info,
    }


def studio_dashboard(db: Session) -> dict:
    ensure_meta_agents(db)
    active_missions = (
        db.query(AgentStudioMission)
        .filter(AgentStudioMission.status == StudioMissionStatus.active)
        .count()
    )
    pending_proposals = (
        db.query(AgentStudioProposal)
        .filter(AgentStudioProposal.status == StudioProposalStatus.pending_review)
        .count()
    )
    total_outcomes = db.query(func.count(AgentStudioOutcome.id)).scalar() or 0

    agents = list_meta_agents(db)
    profiles = []
    for a in agents:
        try:
            profiles.append(get_learning_profile(db, a["entity_id"]))
        except ValueError:
            continue

    return {
        "platform": "agent_studio",
        "version": "1.0",
        "orchestrator_entity_id": NEXUS_ID,
        "loop": ["observe", "evaluate", "refine"],
        "pillars": {
            "learn": "Record outcomes from tests, acceptance, reviews",
            "grow": "Elevate capabilities after sustained success",
            "transform": "Approved proposals update learning profile & playbooks",
            "improve": "Failure-driven proposals trigger refinement",
        },
        "stats": {
            "meta_agents": len(agents),
            "active_missions": active_missions,
            "pending_proposals": pending_proposals,
            "outcomes_recorded": total_outcomes,
        },
        "agents": agents,
        "learning_profiles": profiles,
        "recent_missions": [mission_to_dict(m) for m in list_missions(db, limit=5)],
        "recent_handoffs": [handoff_to_dict(h) for h in list_handoffs(db, limit=8)],
        "pending_proposals": [
            proposal_to_dict(p)
            for p in list_proposals(db, status="pending_review", limit=10)
        ],
        "memory_vault": vault_summary(db),
        "capability_matrix": [
            get_agent_capabilities(db, a["entity_id"])
            for a in agents
        ],
    }
