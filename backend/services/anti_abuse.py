import os
import uuid
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.ai_usage import AIUsageLog
from models.contribution import ContributionEvent

DAILY_CONTRIBUTION_LIMIT = int(os.getenv("DAILY_CONTRIBUTION_LIMIT", "10"))
DAILY_AI_CREDITS_BURN_LIMIT = float(os.getenv("DAILY_AI_CREDITS_BURN_LIMIT", "200"))
DAILY_COMPUTE_JOB_LIMIT = int(os.getenv("DAILY_COMPUTE_JOB_LIMIT", "50"))
HOURLY_COMPUTE_JOB_LIMIT = int(os.getenv("HOURLY_COMPUTE_JOB_LIMIT", "20"))


def require_contribution_bound_compute(
    *,
    contribution_id: str | None,
    task_id: str | None,
) -> None:
    if not contribution_id and not task_id:
        raise HTTPException(
            status_code=400,
            detail="Compute jobs must bind contribution_id or task_id (mesh anti-abuse)",
        )


def check_compute_job_limits(db: Session, entity_id: str) -> None:
    from services.compute_jobs import count_jobs_for_initiator

    daily = count_jobs_for_initiator(db, entity_id, since_hours=24)
    if daily >= DAILY_COMPUTE_JOB_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Daily compute job limit reached: {DAILY_COMPUTE_JOB_LIMIT}",
        )
    hourly = count_jobs_for_initiator(db, entity_id, since_hours=1)
    if hourly >= HOURLY_COMPUTE_JOB_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Hourly compute job limit reached: {HOURLY_COMPUTE_JOB_LIMIT}",
        )


def _day_start() -> datetime:
    now = datetime.utcnow()
    return datetime(now.year, now.month, now.day)


def _evidence_has_content(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, set, tuple)):
        return len(value) > 0
    return bool(value)


def require_evidence(evidence: dict | None) -> None:
    if not evidence or not any(_evidence_has_content(v) for v in evidence.values()):
        raise HTTPException(status_code=400, detail="Evidence is required for contribution submission")


def check_daily_contribution_limit(db: Session, entity_id: str) -> None:
    count = (
        db.query(func.count(ContributionEvent.id))
        .filter(
            ContributionEvent.primary_entity_id == entity_id,
            ContributionEvent.created_at >= _day_start(),
        )
        .scalar()
        or 0
    )
    if count >= DAILY_CONTRIBUTION_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Daily contribution limit reached: {DAILY_CONTRIBUTION_LIMIT}",
        )


def check_daily_ai_burn_limit(db: Session, entity_id: str, next_cost: float) -> None:
    burned = (
        db.query(func.coalesce(func.sum(AIUsageLog.credits_spent), 0.0))
        .filter(
            AIUsageLog.entity_id == entity_id,
            AIUsageLog.created_at >= _day_start(),
        )
        .scalar()
        or 0.0
    )
    if float(burned) + next_cost > DAILY_AI_CREDITS_BURN_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Daily AI Credits burn limit reached: {DAILY_AI_CREDITS_BURN_LIMIT}",
        )


# --- CI-10: Reputation event-sourcing scaffold (open core; no commercial ranking optimizer) ---

REPUTATION_DELTA_TYPES = frozenset({"success", "failure", "dispute"})
REPUTATION_SOURCE_EVENT_TYPES = frozenset(
    {
        "SettlementExecuted",
        "VerificationCompleted",
        "InvocationCompleted",
        "ProofSubmitted",
    }
)
COMMERCIAL_REPUTATION_KEYS = frozenset(
    {
        "ml_rank_weight",
        "optimizer_model",
        "commercial_ranking",
        "ranking_optimizer",
        "neural_rank_score",
    }
)
DAILY_REPUTATION_EVENT_LIMIT = int(os.getenv("DAILY_REPUTATION_EVENT_LIMIT", "100"))


@dataclass(frozen=True)
class ReputationEvent:
    """Append-only reputation ledger entry derived from verified protocol events."""

    event_id: str
    event_type: str
    subject_entity_id: str
    scope: str
    actor_entity_id: str
    source_ref: str
    delta: str


@dataclass
class ReputationSnapshot:
    entity_id: str
    scope: str
    success_count: int = 0
    failure_count: int = 0
    dispute_count: int = 0

    @property
    def score(self) -> float:
        total = self.success_count + self.failure_count + self.dispute_count
        return self.success_count / total if total else 0.0


def block_reputation_self_feedback(subject_entity_id: str, actor_entity_id: str) -> None:
    if subject_entity_id == actor_entity_id:
        raise ValueError("Self-feedback is not allowed for reputation events (ERC-8004 guardrail)")


def require_reputation_source_ref(source_ref: str | None) -> None:
    if not source_ref or not str(source_ref).strip():
        raise ValueError("Reputation events must bind a verified source_ref (invocation/proof/settlement id)")


def reject_commercial_reputation_keys(payload: dict[str, Any] | None) -> None:
    if not payload:
        return
    blocked = COMMERCIAL_REPUTATION_KEYS.intersection(payload.keys())
    if blocked:
        raise ValueError(f"Commercial reputation optimizer keys are not allowed in open core: {sorted(blocked)}")


def validate_reputation_event(event: ReputationEvent) -> None:
    block_reputation_self_feedback(event.subject_entity_id, event.actor_entity_id)
    require_reputation_source_ref(event.source_ref)
    if event.event_type not in REPUTATION_SOURCE_EVENT_TYPES:
        raise ValueError(f"Unsupported reputation source event_type: {event.event_type}")
    if event.delta not in REPUTATION_DELTA_TYPES:
        raise ValueError(f"Invalid reputation delta: {event.delta}")


class ReputationEventStore:
    """Append-only in-memory reputation event log."""

    def __init__(self) -> None:
        self._events: list[ReputationEvent] = []

    def append(self, event: ReputationEvent) -> ReputationEvent:
        validate_reputation_event(event)
        self._events.append(event)
        return event

    @property
    def events(self) -> list[ReputationEvent]:
        return list(self._events)


class ReputationGraphIndexer:
    """Event-sourced reputation projection (count-based; no commercial ML optimizer)."""

    def __init__(self, store: ReputationEventStore | None = None) -> None:
        self.store = store or ReputationEventStore()
        self._snapshots: dict[tuple[str, str], ReputationSnapshot] = {}
        self._daily_counts: dict[str, int] = {}

    def ingest(
        self,
        *,
        event_type: str,
        subject_entity_id: str,
        scope: str,
        actor_entity_id: str,
        source_ref: str,
        delta: str,
        event_id: str | None = None,
    ) -> ReputationSnapshot:
        actor_key = f"{actor_entity_id}:{_day_start().isoformat()}"
        if self._daily_counts.get(actor_key, 0) >= DAILY_REPUTATION_EVENT_LIMIT:
            raise ValueError(
                f"Daily reputation event limit reached: {DAILY_REPUTATION_EVENT_LIMIT}",
            )

        event = ReputationEvent(
            event_id=event_id or f"rep_evt_{uuid.uuid4().hex[:16]}",
            event_type=event_type,
            subject_entity_id=subject_entity_id,
            scope=scope,
            actor_entity_id=actor_entity_id,
            source_ref=source_ref,
            delta=delta,
        )
        self.store.append(event)
        self._daily_counts[actor_key] = self._daily_counts.get(actor_key, 0) + 1
        return self._apply(event)

    def _apply(self, event: ReputationEvent) -> ReputationSnapshot:
        key = (event.subject_entity_id, event.scope)
        snap = self._snapshots.get(key)
        if snap is None:
            snap = ReputationSnapshot(entity_id=event.subject_entity_id, scope=event.scope)
            self._snapshots[key] = snap
        if event.delta == "success":
            snap.success_count += 1
        elif event.delta == "failure":
            snap.failure_count += 1
        else:
            snap.dispute_count += 1
        return snap

    def replay(self) -> dict[tuple[str, str], ReputationSnapshot]:
        rebuilt: dict[tuple[str, str], ReputationSnapshot] = {}
        for event in self.store.events:
            key = (event.subject_entity_id, event.scope)
            snap = rebuilt.get(key)
            if snap is None:
                snap = ReputationSnapshot(entity_id=event.subject_entity_id, scope=event.scope)
                rebuilt[key] = snap
            if event.delta == "success":
                snap.success_count += 1
            elif event.delta == "failure":
                snap.failure_count += 1
            else:
                snap.dispute_count += 1
        self._snapshots = rebuilt
        return dict(rebuilt)

    def get_snapshot(self, entity_id: str, scope: str) -> ReputationSnapshot | None:
        return self._snapshots.get((entity_id, scope))


# --- CI-11: Governance PIP template + weighted vote scaffold ---

GOVERNANCE_PIP_TEMPLATE_V0: dict[str, Any] = {
    "schema_version": "pip-v0",
    "proposal_type": "protocol_improvement",
    "title": "",
    "summary": "",
    "target_spec_paths": [],
    "eligible_roles": [],
    "vote": {
        "quorum_fraction": 0.0,
        "approval_threshold": 0.5,
        "weight_factors": {
            "stake": 1.0,
            "reputation_coefficient": 1.0,
            "recent_contribution_coefficient": 1.0,
            "role_eligibility": 1.0,
            "risk_adjustment": 1.0,
        },
    },
}


def pip_template_v0() -> dict[str, Any]:
    return deepcopy(GOVERNANCE_PIP_TEMPLATE_V0)


def validate_pip_proposal(proposal: dict[str, Any]) -> None:
    required = ("schema_version", "proposal_type", "title", "summary", "vote")
    missing = [k for k in required if k not in proposal]
    if missing:
        raise ValueError(f"PIP proposal missing required fields: {missing}")
    reject_commercial_reputation_keys(proposal)
    if proposal.get("schema_version") != "pip-v0":
        raise ValueError("PIP proposal schema_version must be pip-v0")
    vote = proposal.get("vote")
    if not isinstance(vote, dict):
        raise ValueError("PIP vote block must be an object")
    reject_commercial_reputation_keys(vote)
    reject_commercial_reputation_keys(vote.get("weight_factors") or {})
    factors = vote.get("weight_factors") or {}
    for name, value in factors.items():
        if float(value) < 0:
            raise ValueError(f"PIP weight factor must be non-negative: {name}")


def compute_governance_power(voter: dict[str, float]) -> float:
    """Open-core scaffold aligned with docs/architecture/08-REPUTATION-GOVERNANCE.md."""
    stake = max(0.0, float(voter.get("stake", 0.0)))
    reputation = max(0.0, float(voter.get("reputation_coefficient", 0.0)))
    recent = max(0.0, float(voter.get("recent_contribution_coefficient", 0.0)))
    role = max(0.0, float(voter.get("role_eligibility", 0.0)))
    risk = max(0.0, float(voter.get("risk_adjustment", 0.0)))
    if risk == 0:
        return 0.0
    return stake * reputation * recent * role * risk


def tally_weighted_vote(
    ballots: list[dict[str, Any]],
    voter_context: dict[str, dict[str, float]],
) -> dict[str, Any]:
    """Weighted vote scaffold — advisory only; no on-chain finalization."""
    validate_pip_proposal(
        {
            **GOVERNANCE_PIP_TEMPLATE_V0,
            "title": "tally-scaffold",
            "summary": "internal",
        },
    )
    approve_weight = 0.0
    reject_weight = 0.0
    abstain_weight = 0.0
    for ballot in ballots:
        entity_id = ballot.get("entity_id")
        if not entity_id:
            raise ValueError("Ballot missing entity_id")
        power = compute_governance_power(voter_context.get(entity_id, {}))
        choice = str(ballot.get("ballot", "abstain")).lower()
        if choice == "approve":
            approve_weight += power
        elif choice == "reject":
            reject_weight += power
        else:
            abstain_weight += power
    total = approve_weight + reject_weight + abstain_weight
    return {
        "approve_weight": approve_weight,
        "reject_weight": reject_weight,
        "abstain_weight": abstain_weight,
        "total_weight": total,
        "approved": total > 0 and approve_weight > reject_weight,
        "compat": "pip-v0-scaffold",
    }
