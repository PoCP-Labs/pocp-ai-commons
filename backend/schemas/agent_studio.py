"""Agent Studio API schemas."""

from typing import Any

from pydantic import BaseModel, Field


class MissionCreateIn(BaseModel):
    title: str
    description: str | None = None
    kind: str = "evolve"
    sponsor_entity_id: str | None = None
    orchestrator_entity_id: str | None = None
    goal_metrics: dict[str, Any] = Field(default_factory=dict)


class HandoffCreateIn(BaseModel):
    from_agent_entity_id: str
    to_agent_entity_id: str
    mission_id: str | None = None
    scope: str | None = None
    files_touched: list[str] = Field(default_factory=list)
    tests_run: str | None = None
    blockers: str | None = None


class HandoffCompleteIn(BaseModel):
    status: str = "completed"
    blockers: str | None = None


class OutcomeCreateIn(BaseModel):
    agent_entity_id: str
    kind: str
    result: str
    mission_id: str | None = None
    handoff_id: str | None = None
    score: float | None = None
    summary: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    auto_evaluate: bool = True


class ProposalReviewIn(BaseModel):
    approve: bool
    reviewer_entity_id: str
    review_note: str | None = None


class ProposalApplyIn(BaseModel):
    actor_entity_id: str
