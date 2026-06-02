"""Automatic evolution — memory ingest, outcome proposals, capability growth."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from meta_agents_spec import META_AGENT_IDS, NEXUS_ID
from models.agent_studio import (
    AgentStudioHandoff,
    AgentStudioOutcome,
    AgentStudioProposal,
    StudioHandoffStatus,
    StudioOutcomeResult,
    StudioProposalKind,
    StudioProposalStatus,
)
from services.agent_studio.agent_capabilities import evolve_capability, studio_capability_matrix
from services.agent_studio.evolution import apply_proposal, process_outcome, review_proposal
from services.agent_studio.memory_store import append_memory, vault_summary
def auto_evolution_enabled() -> bool:
    return os.getenv("POCP_STUDIO_AUTO_EVOLVE", "true").lower() in ("1", "true", "yes")


def ingest_handoff_memory(db: Session, handoff: AgentStudioHandoff) -> dict[str, Any] | None:
    if handoff.status not in (StudioHandoffStatus.completed, StudioHandoffStatus.blocked):
        return None
    status = handoff.status.value
    importance = 0.8 if status == "completed" else 0.6
    entry = append_memory(
        db,
        agent_entity_id=handoff.to_agent_entity_id,
        title=f"Handoff {status}: {(handoff.scope or '')[:80]}",
        content=(
            f"From {handoff.from_agent_entity_id} to {handoff.to_agent_entity_id}.\n"
            f"Scope: {handoff.scope or ''}\n"
            f"Tests: {handoff.tests_run or ''}\n"
            f"Blockers: {handoff.blockers or 'none'}"
        ),
        kind="episodic",
        source_type="handoff",
        source_id=handoff.id,
        tags=["handoff", status],
        importance=importance,
    )
    if status == "completed":
        append_memory(
            db,
            scope="studio",
            agent_entity_id=NEXUS_ID,
            title=f"Collective: {handoff.to_agent_entity_id} completed handoff",
            content=(handoff.scope or "")[:1500],
            kind="lesson",
            source_type="handoff",
            source_id=handoff.id,
            tags=["studio", "success"],
            importance=0.55,
        )
    return {"memory_id": entry.id}


def ingest_outcome_memory(db: Session, outcome: AgentStudioOutcome) -> dict[str, Any]:
    result = outcome.result.value
    if result == "pass_":
        result = "pass"
    kind = "lesson" if result == "pass" else "episodic"
    entry = append_memory(
        db,
        agent_entity_id=outcome.agent_entity_id,
        title=f"Outcome {result}: {outcome.kind.value}",
        content=outcome.summary or "",
        kind=kind,
        source_type="outcome",
        source_id=outcome.id,
        tags=["outcome", outcome.kind.value, result],
        importance=0.75 if result == "pass" else 0.65,
        metadata={"evidence_keys": list((outcome.evidence or {}).keys())},
    )
    actions: dict[str, Any] = {"memory_id": entry.id}

    if auto_evolution_enabled():
        proposal = process_outcome(db, outcome.id)
        if proposal is not None:
            actions["proposal_id"] = proposal.id
            if _should_auto_apply(proposal):
                review_proposal(
                    db,
                    proposal.id,
                    approve=True,
                    reviewer_entity_id=NEXUS_ID,
                    review_note="Auto-evolution: Nexus PDCA apply",
                )
                applied = apply_proposal(db, proposal.id, actor_entity_id=NEXUS_ID)
                actions["applied"] = applied
                hints = (proposal.proposed_changes or {}).get("capability_hints") or []
                hint = (proposal.proposed_changes or {}).get("capability_hint")
                if hint:
                    hints = [hint] + list(hints)
                for cap in hints[:3]:
                    if cap:
                        evolve_capability(
                            db,
                            proposal.agent_entity_id,
                            str(cap),
                            source="auto_evolution",
                            evidence={"proposal_id": proposal.id},
                        )
            elif proposal.kind == StudioProposalKind.capability_add and result == "pass":
                hint = (proposal.proposed_changes or {}).get("capability_hint")
                if hint:
                    evolve_capability(
                        db,
                        proposal.agent_entity_id,
                        str(hint),
                        source="growth_streak",
                    )

    return actions


def _should_auto_apply(proposal: AgentStudioProposal) -> bool:
    if proposal.kind in (
        StudioProposalKind.skill_sync,
        StudioProposalKind.capability_add,
    ):
        return True
    if proposal.kind == StudioProposalKind.prompt_refine:
        return os.getenv("POCP_STUDIO_AUTO_APPLY_IMPROVE", "false").lower() in (
            "1",
            "true",
            "yes",
        )
    return False


def run_auto_evolution_tick(db: Session, *, limit_outcomes: int = 20) -> dict[str, Any]:
    """Process recent outcomes without memory ingest flag; compact evolution pass."""
    if not auto_evolution_enabled():
        return {"ran": False, "reason": "POCP_STUDIO_AUTO_EVOLVE disabled"}

    recent = (
        db.query(AgentStudioOutcome)
        .order_by(AgentStudioOutcome.created_at.desc())
        .limit(limit_outcomes)
        .all()
    )
    processed = 0
    memories = 0
    proposals_applied = 0
    for outcome in recent:
        meta = outcome.metadata_ or {}
        if meta.get("memory_ingested"):
            continue
        ingest_outcome_memory(db, outcome)
        meta["memory_ingested"] = True
        outcome.metadata_ = meta
        memories += 1
        processed += 1

    pending_grow = (
        db.query(AgentStudioProposal)
        .filter(
            AgentStudioProposal.status == StudioProposalStatus.pending_review,
            AgentStudioProposal.kind == StudioProposalKind.capability_add,
        )
        .limit(5)
        .all()
    )
    for proposal in pending_grow:
        review_proposal(
            db,
            proposal.id,
            approve=True,
            reviewer_entity_id=NEXUS_ID,
            review_note="Auto-evolution: growth proposal",
        )
        apply_proposal(db, proposal.id, actor_entity_id=NEXUS_ID)
        proposals_applied += 1

    return {
        "ran": True,
        "outcomes_processed": processed,
        "memories_written": memories,
        "proposals_auto_applied": proposals_applied,
        "vault": vault_summary(db),
        "capability_matrix": studio_capability_matrix(db),
    }
