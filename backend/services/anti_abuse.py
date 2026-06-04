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
        "ExchangeSettled",
    }
)
FEDERATION_REPUTATION_READ_SCHEMA = "federation-reputation-read-v0"
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

# --- PA-6 / CIP-P3.2: MCP invoke security baseline (open core) ---
HOURLY_MCP_INVOKE_LIMIT = int(os.getenv("HOURLY_MCP_INVOKE_LIMIT", "30"))
DAILY_MCP_INVOKE_LIMIT = int(os.getenv("DAILY_MCP_INVOKE_LIMIT", "200"))
MCP_INVOKE_CAPABILITY = "mcp_tool_call"
MCP_PROVIDER_PREFIX = "mcp-"


def _hour_start() -> datetime:
    now = datetime.utcnow()
    return datetime(now.year, now.month, now.day, now.hour)


def _count_mcp_invocations(db: Session, entity_id: str, *, since: datetime) -> int:
    from models.invocation import InvocationTrace

    return (
        db.query(func.count(InvocationTrace.id))
        .filter(
            InvocationTrace.initiator_id == entity_id,
            InvocationTrace.created_at >= since,
            InvocationTrace.model_provider.like(f"{MCP_PROVIDER_PREFIX}%"),
        )
        .scalar()
        or 0
    )


def check_mcp_invoke_rate_limit(db: Session, entity_id: str) -> None:
    """Per-initiator MCP invoke rate limits (InvocationTrace model_provider mcp-*)."""
    hourly = _count_mcp_invocations(db, entity_id, since=_hour_start())
    if hourly >= HOURLY_MCP_INVOKE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Hourly MCP invoke limit reached: {HOURLY_MCP_INVOKE_LIMIT}",
        )
    daily = _count_mcp_invocations(db, entity_id, since=_day_start())
    if daily >= DAILY_MCP_INVOKE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Daily MCP invoke limit reached: {DAILY_MCP_INVOKE_LIMIT}",
        )


def enforce_mcp_invoke_auth_scope(
    db: Session,
    *,
    authenticated_entity_id: str,
    human_entity_id: str,
    agent_entity_id: str | None,
    tool_entity_id: str,
) -> None:
    """Auth scope: session entity must match human initiator; agent/tool chain validated."""
    from models.entity import Entity, EntityType

    if authenticated_entity_id != human_entity_id:
        raise HTTPException(
            status_code=403,
            detail="MCP invoke auth scope: initiator must match authenticated entity",
        )
    human = db.get(Entity, human_entity_id)
    if not human or human.entity_type != EntityType.human:
        raise HTTPException(status_code=400, detail="Initiator must be a human entity")
    if agent_entity_id:
        agent = db.get(Entity, agent_entity_id)
        if not agent or agent.entity_type != EntityType.agent:
            raise HTTPException(status_code=404, detail="Agent entity not found")
        allowed_agents = (human.metadata_ or {}).get("mcp_allowed_agent_ids")
        if allowed_agents is not None and agent_entity_id not in allowed_agents:
            raise HTTPException(
                status_code=403,
                detail="MCP invoke auth scope: agent not in human mcp_allowed_agent_ids",
            )
    tool = db.get(Entity, tool_entity_id)
    if tool:
        scopes = (tool.metadata_ or {}).get("auth_scopes")
        if scopes is not None and MCP_INVOKE_CAPABILITY not in scopes:
            raise HTTPException(
                status_code=403,
                detail=f"MCP tool missing required auth scope: {MCP_INVOKE_CAPABILITY}",
            )


def mcp_invoke_receipt_audit_fields(
    *,
    trace_id: str,
    invoke_mode: str,
    provider: str,
    tool_entity_id: str,
) -> dict[str, Any]:
    """Receipt logging metadata for MCP invoke steps (PA-6 audit trail)."""
    return {
        "audit_kind": "mcp_invoke",
        "trace_id": trace_id,
        "invoke_mode": invoke_mode,
        "provider": provider,
        "tool_entity_id": tool_entity_id,
        "capability": MCP_INVOKE_CAPABILITY,
        "compat": "pa-6-mcp-security-v0",
    }


def enforce_mcp_invoke_baseline(
    db: Session,
    *,
    authenticated_entity_id: str,
    human_entity_id: str,
    agent_entity_id: str | None,
    tool_entity_id: str,
) -> None:
    """PA-6 MCP security baseline: auth scope + rate limits before invoke."""
    enforce_mcp_invoke_auth_scope(
        db,
        authenticated_entity_id=authenticated_entity_id,
        human_entity_id=human_entity_id,
        agent_entity_id=agent_entity_id,
        tool_entity_id=tool_entity_id,
    )
    check_mcp_invoke_rate_limit(db, human_entity_id)


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


def reputation_scope_from_exchange_payload(payload: dict[str, Any]) -> str:
    """Derive contextual reputation scope from exchange_settled payload."""
    cap = payload.get("capability") or payload.get("capability_id")
    if cap:
        return str(cap)
    kind = payload.get("exchange_kind")
    if kind:
        return str(kind)
    return "exchange"


def reputation_delta_from_exchange_payload(payload: dict[str, Any]) -> str:
    """Map exchange_settled usage to reputation delta (stub; no ML optimizer)."""
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    status = str(usage.get("status") or usage.get("outcome") or "").lower()
    if status in {"failed", "failure", "error", "rejected"}:
        return "failure"
    if status in {"dispute", "disputed", "contested"}:
        return "dispute"
    return "success"


def exchange_settled_reputation_fields(
    payload: dict[str, Any],
    *,
    ledger_record_id: str | None = None,
) -> dict[str, str] | None:
    """Extract reputation indexer fields from one exchange_settled payload."""
    if not isinstance(payload, dict):
        return None
    reject_commercial_reputation_keys(payload)

    exchange_id = str(payload.get("exchange_id") or "").strip()
    consumer_id = str(payload.get("consumer_entity_id") or "").strip()
    providers = payload.get("provider_entity_ids")
    provider_id = ""
    if isinstance(providers, list) and providers:
        provider_id = str(providers[0] or "").strip()
    if not exchange_id or not consumer_id or not provider_id:
        return None
    if consumer_id == provider_id:
        return None

    return {
        "event_type": "ExchangeSettled",
        "subject_entity_id": provider_id,
        "scope": reputation_scope_from_exchange_payload(payload),
        "actor_entity_id": consumer_id,
        "source_ref": exchange_id,
        "delta": reputation_delta_from_exchange_payload(payload),
        "ledger_record_id": ledger_record_id or exchange_id,
    }


class FederationReputationReadIndexer:
    """CIP-P4.3 — read-only reputation projection from exchange_settled ledger rows."""

    def __init__(self, indexer: ReputationGraphIndexer | None = None) -> None:
        self.indexer = indexer or ReputationGraphIndexer()
        self._indexed_exchange_ids: set[str] = set()
        self._peer_route_count = 0
        self._skipped_self_feedback = 0

    def index_exchange_settled_payload(
        self,
        payload: dict[str, Any],
        *,
        ledger_record_id: str | None = None,
    ) -> ReputationSnapshot | None:
        fields = exchange_settled_reputation_fields(payload, ledger_record_id=ledger_record_id)
        if fields is None:
            consumer_id = str(payload.get("consumer_entity_id") or "").strip()
            providers = payload.get("provider_entity_ids")
            provider_id = ""
            if isinstance(providers, list) and providers:
                provider_id = str(providers[0] or "").strip()
            if consumer_id and provider_id and consumer_id == provider_id:
                self._skipped_self_feedback += 1
            return None

        exchange_id = fields["source_ref"]
        if exchange_id in self._indexed_exchange_ids:
            return self.indexer.get_snapshot(fields["subject_entity_id"], fields["scope"])

        if payload.get("peer_route"):
            self._peer_route_count += 1

        snap = self.indexer.ingest(
            event_type=fields["event_type"],
            subject_entity_id=fields["subject_entity_id"],
            scope=fields["scope"],
            actor_entity_id=fields["actor_entity_id"],
            source_ref=fields["source_ref"],
            delta=fields["delta"],
            event_id=f"rep_ex_{fields['ledger_record_id']}",
        )
        self._indexed_exchange_ids.add(exchange_id)
        return snap

    def index_ledger_record(self, record: Any) -> ReputationSnapshot | None:
        event_type = getattr(record, "event_type", None)
        if event_type != "exchange_settled":
            return None
        payload = getattr(record, "payload", None)
        if not isinstance(payload, dict):
            return None
        return self.index_exchange_settled_payload(
            payload,
            ledger_record_id=getattr(record, "id", None),
        )

    def index_from_db(self, db: Session, *, limit: int = 500) -> "FederationReputationReadIndexer":
        from models.ledger import LedgerRecord

        rows = (
            db.query(LedgerRecord)
            .filter(LedgerRecord.event_type == "exchange_settled")
            .order_by(LedgerRecord.created_at.asc())
            .limit(max(1, int(limit)))
            .all()
        )
        for row in rows:
            self.index_ledger_record(row)
        return self

    def read_model(self) -> dict[str, Any]:
        snapshots = [
            {
                "entity_id": snap.entity_id,
                "scope": snap.scope,
                "success_count": snap.success_count,
                "failure_count": snap.failure_count,
                "dispute_count": snap.dispute_count,
                "score": round(snap.score, 4),
            }
            for snap in sorted(
                self.indexer._snapshots.values(),
                key=lambda item: (item.entity_id, item.scope),
            )
        ]
        return {
            "schema_version": FEDERATION_REPUTATION_READ_SCHEMA,
            "indexed_exchange_count": len(self._indexed_exchange_ids),
            "peer_route_exchange_count": self._peer_route_count,
            "skipped_self_feedback": self._skipped_self_feedback,
            "snapshot_count": len(snapshots),
            "snapshots": snapshots,
            "compat": "cip-p4.3-federation-reputation-read-stub",
        }


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
