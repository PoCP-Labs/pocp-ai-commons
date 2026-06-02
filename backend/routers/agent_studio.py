"""Agent Studio sub-platform — self-learning Meta Agent orchestration."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.agent import Agent
from models.agent_studio import AgentStudioProposal
from schemas.agent_studio import (
    HandoffCompleteIn,
    HandoffCreateIn,
    MissionCreateIn,
    OutcomeCreateIn,
    ProposalApplyIn,
    ProposalReviewIn,
)
from services.agent_studio.evolution import (
    apply_proposal,
    get_learning_profile,
    process_outcome,
    review_proposal,
    studio_dashboard,
)
from services.agent_studio.patch_suggestions import build_patch_markdown
from services.agent_studio.handoffs import (
    complete_handoff,
    create_handoff,
    handoff_to_dict,
    list_handoffs,
)
from services.agent_studio.mission_plans import (
    create_mission_from_plan,
    list_mission_plans,
    spawn_plan_handoffs,
)
from services.agent_studio.nexus_autopilot import (
    PROJECT_NORTH_STAR,
    list_project_goals,
    nexus_pm_status,
    run_nexus_autopilot,
)
from services.agent_studio.nexus_super_loop import (
    last_super_tick,
    run_nexus_super_tick,
    super_loop_status,
)
from services.agent_studio.nexus_learning import (
    nexus_learning_status,
    review_project_progress,
    run_nexus_learning_cycle,
)
from services.agent_studio.cursor_automation import (
    automation_status,
    count_pending_for_cursor,
    last_automation_tick,
    pick_pending_handoffs,
    run_cursor_automation_tick,
)
from services.agent_studio.cursor_bridge import automation_enabled
from services.agent_studio.missions import (
    activate_mission,
    create_mission,
    get_mission,
    list_missions,
    mission_to_dict,
)
from services.agent_studio.agent_capabilities import (
    evolve_capability,
    get_agent_capabilities,
    studio_capability_matrix,
)
from services.agent_studio.auto_evolution import run_auto_evolution_tick
from services.agent_studio.memory_store import append_memory, list_memories, memory_to_dict, vault_summary
from services.agent_studio.outcomes import outcome_to_dict, record_outcome
from services.agent_studio.proposals import list_proposals, proposal_to_dict
from services.meta_agent_registry import ensure_meta_agents, get_meta_agent, list_meta_agents

router = APIRouter(prefix="/api/v1/agent-studio", tags=["agent-studio"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    ensure_meta_agents(db)
    payload = studio_dashboard(db)
    payload["nexus_pm"] = nexus_pm_status(db)
    payload["cursor_automation"] = {
        **automation_status(),
        "pending_for_cursor": count_pending_for_cursor(db),
        "last_tick": last_automation_tick(),
    }
    payload["super_loop"] = super_loop_status()
    return payload


@router.get("/nexus/status")
def nexus_status(db: Session = Depends(get_db)):
    ensure_meta_agents(db)
    return nexus_pm_status(db)


@router.get("/nexus/goals")
def nexus_goals():
    return {"north_star": PROJECT_NORTH_STAR, "goals": list_project_goals()}


@router.get("/nexus/progress-review")
def nexus_progress_review(db: Session = Depends(get_db)):
    ensure_meta_agents(db)
    return review_project_progress(db)


@router.get("/nexus/learning")
def nexus_learning(db: Session = Depends(get_db)):
    ensure_meta_agents(db)
    return nexus_learning_status(db)


@router.post("/nexus/learning-cycle")
def nexus_learning_cycle_endpoint(
    db: Session = Depends(get_db),
    mission_id: str | None = Query(default=None),
):
    ensure_meta_agents(db)
    result = run_nexus_learning_cycle(db, mission_id=mission_id)
    db.commit()
    return result


@router.get("/cursor/status")
def cursor_automation_status(db: Session = Depends(get_db)):
    return {
        **automation_status(),
        "pending_for_cursor": count_pending_for_cursor(db),
        "last_tick": last_automation_tick(),
    }


@router.get("/cursor/pending")
def cursor_pending_handoffs(
    db: Session = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=50),
):
    return [
        handoff_to_dict(h)
        for h in pick_pending_handoffs(db, limit=limit)
    ]


@router.post("/cursor/run")
def cursor_run_pending(
    db: Session = Depends(get_db),
    max_handoffs: int = Query(default=1, ge=1, le=3),
    verbose: bool = Query(default=False, description="Stream logs to server stdout"),
):
    if not automation_enabled():
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Cursor automation inactive",
                "status": automation_status(),
            },
        )
    try:
        result = run_cursor_automation_tick(db, max_handoffs=max_handoffs, verbose=verbose)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result


@router.get("/automation/status")
def studio_automation_status(db: Session = Depends(get_db)):
    """Single pane: host vs Docker loops, Cursor readiness, pending work."""
    ensure_meta_agents(db)
    from services.agent_studio.nexus_super_loop import (
        cursor_backend_automation_enabled,
        last_super_tick,
        super_loop_backend_enabled,
        super_loop_host_mode,
    )

    cursor = {
        **automation_status(),
        "pending_for_cursor": count_pending_for_cursor(db),
        "last_tick": last_automation_tick(),
    }
    return {
        "host_mode": super_loop_host_mode(),
        "docker_super_loop": super_loop_backend_enabled(),
        "docker_cursor_loop": cursor_backend_automation_enabled(),
        "recommended_action": (
            "Run .\\scripts\\start-agent-studio-automation.ps1 on Windows host"
            if super_loop_host_mode()
            else "Set POCP_NEXUS_SUPER_LOOP=true or POCP_NEXUS_SUPER_LOOP_HOST=true in backend/.env"
        ),
        "cursor": cursor,
        "super_loop": super_loop_status(),
        "last_super_tick": last_super_tick(),
        "nexus_pm": nexus_pm_status(db),
    }


@router.get("/nexus/super-loop/status")
def nexus_super_loop_status_endpoint():
    return super_loop_status()


@router.post("/nexus/super-tick")
def nexus_super_tick_endpoint(
    db: Session = Depends(get_db),
    sponsor_entity_id: str | None = Query(default=None),
    force_new_mission: bool = Query(default=False),
    max_cursor_handoffs: int = Query(default=2, ge=0, le=5),
):
    """Full PDCA super-loop: plan → Cursor execute → check → learn → platform heal."""
    ensure_meta_agents(db)
    try:
        result = run_nexus_super_tick(
            db,
            sponsor_entity_id=sponsor_entity_id,
            force_new_mission=force_new_mission,
            max_cursor_handoffs=max_cursor_handoffs,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result


@router.get("/nexus/super-loop/last")
def nexus_super_loop_last():
    tick = last_super_tick()
    if not tick:
        return {"ran": False, "message": "No super-loop tick recorded yet."}
    return tick


@router.post("/nexus/autopilot")
def nexus_autopilot(
    db: Session = Depends(get_db),
    sponsor_entity_id: str | None = Query(default=None),
    force_new_mission: bool = Query(default=False),
):
    """Nexus-0 PM tick: decompose roadmap, start/advance missions, dispatch handoffs."""
    ensure_meta_agents(db)
    try:
        result = run_nexus_autopilot(
            db,
            sponsor_entity_id=sponsor_entity_id,
            force_new_mission=force_new_mission,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.post("/ensure-agents")
def ensure_agents(db: Session = Depends(get_db)):
    ids = ensure_meta_agents(db)
    db.commit()
    return {"ensured": ids, "count": len(ids)}


@router.get("/agents")
def studio_agents(db: Session = Depends(get_db)):
    ensure_meta_agents(db)
    return list_meta_agents(db)


@router.get("/agents/{entity_id}")
def studio_agent(entity_id: str, db: Session = Depends(get_db)):
    ensure_meta_agents(db)
    row = get_meta_agent(db, entity_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Meta Agent not found")
    row["learning_profile"] = get_learning_profile(db, entity_id)
    return row


@router.get("/agents/{entity_id}/learning-profile")
def learning_profile(entity_id: str, db: Session = Depends(get_db)):
    try:
        return get_learning_profile(db, entity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/agents/{entity_id}/capabilities")
def agent_capabilities(entity_id: str, db: Session = Depends(get_db)):
    try:
        return get_agent_capabilities(db, entity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/agents/{entity_id}/memories")
def agent_memories(
    entity_id: str,
    db: Session = Depends(get_db),
    limit: int = Query(default=30, ge=1, le=100),
    kind: str | None = Query(default=None),
):
    rows = list_memories(db, agent_entity_id=entity_id, kind=kind, limit=limit)
    return [memory_to_dict(m) for m in rows]


@router.post("/agents/{entity_id}/memories", status_code=201)
def create_agent_memory(
    entity_id: str,
    db: Session = Depends(get_db),
    title: str = Query(..., min_length=3),
    content: str | None = Query(default=None),
    kind: str = Query(default="semantic"),
):
    try:
        entry = append_memory(
            db,
            agent_entity_id=entity_id,
            title=title,
            content=content,
            kind=kind,
            source_type="manual",
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return memory_to_dict(entry)


@router.get("/memory-vault")
def memory_vault(db: Session = Depends(get_db)):
    ensure_meta_agents(db)
    return vault_summary(db)


@router.get("/capability-matrix")
def capability_matrix(db: Session = Depends(get_db)):
    ensure_meta_agents(db)
    return studio_capability_matrix(db)


@router.post("/evolution/tick")
def evolution_tick(db: Session = Depends(get_db)):
    """Auto-evolution: ingest outcomes → memory → proposals → capability growth."""
    ensure_meta_agents(db)
    try:
        result = run_auto_evolution_tick(db)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result


@router.get("/missions")
def missions(db: Session = Depends(get_db)):
    return [mission_to_dict(m) for m in list_missions(db)]


@router.post("/missions", status_code=201)
def create_mission_endpoint(body: MissionCreateIn, db: Session = Depends(get_db)):
    mission = create_mission(
        db,
        title=body.title,
        description=body.description,
        kind=body.kind,
        sponsor_entity_id=body.sponsor_entity_id,
        orchestrator_entity_id=body.orchestrator_entity_id,
        goal_metrics=body.goal_metrics,
    )
    db.commit()
    return mission_to_dict(mission)


@router.post("/missions/{mission_id}/activate")
def activate_mission_endpoint(mission_id: str, db: Session = Depends(get_db)):
    try:
        mission = activate_mission(db, mission_id)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return mission_to_dict(mission)


@router.get("/mission-plans")
def mission_plans_list():
    return list_mission_plans()


@router.post("/missions/from-plan/{plan_id}", status_code=201)
def mission_from_plan(
    plan_id: str,
    sponsor_entity_id: str | None = Query(default=None),
    title: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    try:
        result = create_mission_from_plan(
            db,
            plan_id,
            title_override=title,
            sponsor_entity_id=sponsor_entity_id,
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.post("/missions/{mission_id}/spawn-handoffs")
def spawn_handoffs_endpoint(
    mission_id: str,
    plan_id: str = Query(..., description="e.g. phase_a_p0, phase_a_full"),
    db: Session = Depends(get_db),
):
    mission = get_mission(db, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    try:
        handoffs = spawn_plan_handoffs(db, mission_id, plan_id)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"mission_id": mission_id, "plan_id": plan_id, "handoffs": handoffs, "count": len(handoffs)}


@router.get("/missions/{mission_id}")
def mission_detail(mission_id: str, db: Session = Depends(get_db)):
    mission = get_mission(db, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission_to_dict(mission)


@router.get("/handoffs")
def handoffs(mission_id: str | None = None, db: Session = Depends(get_db)):
    return [handoff_to_dict(h) for h in list_handoffs(db, mission_id=mission_id)]


@router.post("/handoffs", status_code=201)
def create_handoff_endpoint(body: HandoffCreateIn, db: Session = Depends(get_db)):
    try:
        handoff = create_handoff(
            db,
            from_agent_entity_id=body.from_agent_entity_id,
            to_agent_entity_id=body.to_agent_entity_id,
            mission_id=body.mission_id,
            scope=body.scope,
            files_touched=body.files_touched,
            tests_run=body.tests_run,
            blockers=body.blockers,
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return handoff_to_dict(handoff)


@router.post("/handoffs/{handoff_id}/complete")
def complete_handoff_endpoint(
    handoff_id: str, body: HandoffCompleteIn, db: Session = Depends(get_db)
):
    try:
        handoff = complete_handoff(
            db, handoff_id, status=body.status, blockers=body.blockers
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return handoff_to_dict(handoff)


@router.post("/outcomes", status_code=201)
def create_outcome_endpoint(body: OutcomeCreateIn, db: Session = Depends(get_db)):
    try:
        outcome = record_outcome(
            db,
            agent_entity_id=body.agent_entity_id,
            kind=body.kind,
            result=body.result,
            mission_id=body.mission_id,
            handoff_id=body.handoff_id,
            score=body.score,
            summary=body.summary,
            evidence=body.evidence,
        )
        proposal = None
        if body.auto_evaluate:
            proposal = process_outcome(db, outcome.id)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = {"outcome": outcome_to_dict(outcome)}
    if proposal is not None:
        payload["proposal"] = proposal_to_dict(proposal)
    return payload


@router.post("/outcomes/{outcome_id}/evaluate")
def evaluate_outcome_endpoint(outcome_id: str, db: Session = Depends(get_db)):
    try:
        proposal = process_outcome(db, outcome_id)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if proposal is None:
        return {"proposal": None, "message": "No proposal generated"}
    return {"proposal": proposal_to_dict(proposal)}


@router.get("/proposals")
def proposals(
    agent_entity_id: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    return [
        proposal_to_dict(p)
        for p in list_proposals(db, agent_entity_id=agent_entity_id, status=status)
    ]


@router.post("/proposals/{proposal_id}/review")
def review_proposal_endpoint(
    proposal_id: str, body: ProposalReviewIn, db: Session = Depends(get_db)
):
    try:
        proposal = review_proposal(
            db,
            proposal_id,
            approve=body.approve,
            reviewer_entity_id=body.reviewer_entity_id,
            review_note=body.review_note,
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return proposal_to_dict(proposal)


@router.get("/proposals/{proposal_id}/patch-preview")
def patch_preview_endpoint(proposal_id: str, db: Session = Depends(get_db)):
    proposal = db.get(AgentStudioProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    agent = db.query(Agent).filter(Agent.entity_id == proposal.agent_entity_id).first()
    profile = (agent.config or {}).get("learning_profile", {}) if agent else {}
    version = int(profile.get("evolution_version", 0)) + 1
    markdown = build_patch_markdown(
        proposal,
        agent,
        actor_entity_id="preview",
        evolution_version=version,
    )
    return {"proposal_id": proposal_id, "markdown": markdown}


@router.post("/proposals/{proposal_id}/apply")
def apply_proposal_endpoint(
    proposal_id: str, body: ProposalApplyIn, db: Session = Depends(get_db)
):
    try:
        result = apply_proposal(db, proposal_id, actor_entity_id=body.actor_entity_id)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result
