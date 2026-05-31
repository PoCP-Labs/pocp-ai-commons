"""Distributed compute API — Entity providers, job scheduling, heartbeats."""

import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from intelligence import capability_layer
from models.user_account import UserAccount
from routers.auth import current_user_from_header, require_current_user


def optional_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> UserAccount | None:
    if not authorization:
        return None
    try:
        return current_user_from_header(authorization, db)
    except HTTPException:
        return None

router = APIRouter(prefix="/api/v1/compute", tags=["compute"])


class ComputeJobRequest(BaseModel):
    capability: str = Field(
        description="llm_inference | embeddings | witness | mcp_host | agent_runtime | training"
    )
    contribution_id: str | None = None
    task_id: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)


class ComputeHeartbeatRequest(BaseModel):
    status: str = Field(default="active", description="active | idle | offline")


class ComputeRegisterRequest(BaseModel):
    offers: list[dict[str, Any]]
    endpoints: dict[str, Any] = Field(default_factory=dict)
    capacity: dict[str, Any] = Field(default_factory=dict)
    policy: dict[str, Any] = Field(default_factory=dict)
    accountability: dict[str, Any] = Field(default_factory=dict)
    status: str = "active"


@router.post("/providers/refresh-liveness")
def refresh_compute_liveness(db: Session = Depends(get_db)):
    """Mark stale compute profiles offline (heartbeat timeout)."""
    from services.compute_profile import refresh_provider_liveness

    updated = refresh_provider_liveness(db)
    db.commit()
    return {"updated": updated, "stale_policy_seconds": int(os.getenv("POCP_COMPUTE_HEARTBEAT_STALE_SECONDS", "900"))}


@router.get("/providers")
def list_providers(
    capability: str | None = None,
    status: str = "active",
    organization_entity_id: str | None = None,
    mesh_filter: bool = False,
    db: Session = Depends(get_db),
    current_user: UserAccount | None = Depends(optional_current_user),
):
    """Discover Entity-attached compute providers (org-scoped mesh when mesh_filter=true)."""
    if mesh_filter and current_user is None:
        raise HTTPException(status_code=401, detail="mesh_filter requires authentication")
    return capability_layer.list_compute_providers(
        db,
        capability=capability,
        status=status,
        initiator_entity_id=current_user.entity_id if mesh_filter and current_user else None,
        organization_entity_id=organization_entity_id,
        mesh_filter=mesh_filter,
    )


@router.get("/providers/federation")
def list_federated_providers(refresh: bool = False):
    """Mirror compute providers advertised by trusted federation peers."""
    from services.compute_federation import list_federated_compute_providers

    return list_federated_compute_providers(refresh=refresh)


@router.get("/discovery/lan")
def discover_lan_peers(probe: bool = True):
    """Optional campus LAN compute discovery (static + mDNS advisory)."""
    from services.compute_lan_discovery import discover_lan_compute_peers

    return discover_lan_compute_peers(probe=probe)


@router.get("/match")
def match_compute_providers(
    task_id: str | None = None,
    contribution_type: str | None = None,
    limit: int = 3,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Recommend complementary compute providers for a task (Phase γ)."""
    from services.compute_matching import recommend_compute_providers

    return recommend_compute_providers(
        db,
        task_id=task_id,
        contribution_type=contribution_type,
        initiator_entity_id=current_user.entity_id,
        limit_per_capability=limit,
    )


@router.post("/jobs")
def submit_compute_job(
    body: ComputeJobRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Schedule advisory compute job — selects provider, returns ComputeReceipt stub."""
    from services.anti_abuse import check_compute_job_limits, require_contribution_bound_compute

    require_contribution_bound_compute(
        contribution_id=body.contribution_id,
        task_id=body.task_id,
    )
    check_compute_job_limits(db, current_user.entity_id)

    result = capability_layer.schedule_compute_job(
        db,
        capability=body.capability,
        initiator_entity_id=current_user.entity_id,
        contribution_id=body.contribution_id,
        task_id=body.task_id,
        constraints=body.constraints,
    )
    if result.get("status") == "no_provider":
        raise HTTPException(status_code=503, detail="No compute provider available for capability")
    return result


class ComputeExecuteRequest(BaseModel):
    context: dict = Field(default_factory=dict)


class AdapterImportRequest(BaseModel):
    display_name: str | None = None
    entity_id: str | None = Field(default=None, max_length=36)
    external_provider_id: str | None = None
    offers: list[dict[str, Any]] | None = None
    endpoints: dict[str, Any] = Field(default_factory=dict)
    capacity: dict[str, Any] = Field(default_factory=dict)
    policy: dict[str, Any] = Field(default_factory=dict)
    external: dict[str, Any] = Field(default_factory=dict)
    models: list[str] = Field(default_factory=list)
    summary: str | None = None
    status: str = "active"


class AdapterJobRequest(BaseModel):
    capability: str = "llm_inference"
    provider_entity_id: str
    contribution_id: str | None = None
    task_id: str | None = None
    trace_id: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)


@router.get("/adapters")
def list_compute_adapters():
    """Catalog of external compute network adapters (Akash, Render, …)."""
    from services.compute_adapters.service import list_adapter_catalog

    return list_adapter_catalog()


@router.post("/adapters/{slug}/import")
def import_compute_adapter_provider(
    slug: str,
    body: AdapterImportRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Register external network provider as community Entity + compute_profile."""
    from services.compute_adapters.service import import_adapter_provider

    try:
        result = import_adapter_provider(
            db,
            slug,
            body.model_dump(exclude_none=True),
            owner_entity_id=current_user.entity_id,
        )
        db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/adapters/{slug}/jobs")
def submit_adapter_compute_job(
    slug: str,
    body: AdapterJobRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Submit contribution-bound job to external adapter (stub or live)."""
    from services.anti_abuse import check_compute_job_limits, require_contribution_bound_compute
    from services.compute_adapters.service import submit_adapter_job

    require_contribution_bound_compute(
        contribution_id=body.contribution_id,
        task_id=body.task_id,
    )
    check_compute_job_limits(db, current_user.entity_id)

    try:
        result = submit_adapter_job(
            db,
            slug,
            capability=body.capability,
            requester_entity_id=current_user.entity_id,
            provider_entity_id=body.provider_entity_id,
            contribution_id=body.contribution_id,
            task_id=body.task_id,
            trace_id=body.trace_id,
            constraints=body.constraints,
        )
        db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/adapters/{slug}/jobs/{job_id}/poll")
def poll_adapter_compute_job(
    slug: str,
    job_id: str,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Poll external adapter job; completes PoCP ComputeReceipt when ready."""
    from services.compute_adapters.service import poll_adapter_job
    from services.compute_jobs import get_job_record

    existing = get_job_record(db, job_id)
    if existing.get("initiator_entity_id") != current_user.entity_id:
        raise HTTPException(status_code=403, detail="Not authorized to poll this job")

    job = poll_adapter_job(db, slug, job_id)
    db.commit()
    return job


@router.get("/jobs/{job_id}")
def get_compute_job(job_id: str, db: Session = Depends(get_db)):
    """Fetch scheduled compute job + receipt."""
    return capability_layer.get_compute_job(db, job_id)


@router.post("/jobs/{job_id}/execute")
async def execute_compute_job_route(
    job_id: str,
    body: ComputeExecuteRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Execute a scheduled witness job on selected provider."""
    from services.compute_executor import execute_compute_job as run_job

    return await run_job(db, job_id, context=body.context)


@router.post("/entities/{entity_id}/register")
def register_entity_compute(
    entity_id: str,
    body: ComputeRegisterRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Register ComputeProfile on an Entity (Tool, LLM, Organization lab GPU, etc.)."""
    entity = capability_layer.register_compute_profile(
        db,
        entity_id=entity_id,
        profile=body.model_dump(),
        owner_entity_id=current_user.entity_id,
    )
    db.commit()
    db.refresh(entity)
    return {
        "entity_id": entity.id,
        "compute_profile": (entity.metadata_ or {}).get("compute_profile"),
        "principle": capability_layer.principle,
    }


@router.post("/entities/{entity_id}/heartbeat")
def heartbeat_entity_compute(
    entity_id: str,
    body: ComputeHeartbeatRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    entity = capability_layer.heartbeat_compute_profile(
        db,
        entity_id=entity_id,
        status=body.status,
        owner_entity_id=current_user.entity_id,
    )
    db.commit()
    return {
        "entity_id": entity.id,
        "compute_profile": (entity.metadata_ or {}).get("compute_profile"),
    }


class CapacityReservationRequest(BaseModel):
    provider_entity_id: str
    capability: str = "llm_inference"
    window_start: str
    window_end: str
    slots: int = 1
    prepaid_credits: float = 0.0
    contribution_id: str | None = None
    task_id: str | None = None


@router.post("/capacity/reservations")
def create_capacity_reservation(
    body: CapacityReservationRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Book a provider time window (v0.2 draft — in-memory)."""
    from services.anti_abuse import require_contribution_bound_compute
    from services.compute_capacity import create_reservation

    require_contribution_bound_compute(
        contribution_id=body.contribution_id,
        task_id=body.task_id,
    )
    record = create_reservation(
        consumer_entity_id=current_user.entity_id,
        provider_entity_id=body.provider_entity_id,
        capability=body.capability,
        window_start=body.window_start,
        window_end=body.window_end,
        slots=body.slots,
        prepaid_credits=body.prepaid_credits,
        contribution_id=body.contribution_id,
        task_id=body.task_id,
    )
    return record


@router.get("/capacity/reservations")
def list_capacity_reservations(
    provider_entity_id: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    from services.compute_capacity import list_reservations

    return list_reservations(
        consumer_entity_id=current_user.entity_id,
        provider_entity_id=provider_entity_id,
        status=status,
    )


@router.delete("/capacity/reservations/{reservation_id}")
def cancel_capacity_reservation(
    reservation_id: str,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    from services.compute_capacity import cancel_reservation

    return cancel_reservation(reservation_id, consumer_entity_id=current_user.entity_id)


@router.get("/artifacts")
def list_compute_artifacts(
    limit: int = 50,
    current_user: UserAccount = Depends(require_current_user),
):
    """List cached ComputeArtifacts (operator/debug — v0.2 prototype)."""
    from services.compute_artifact import list_artifacts

    items = list_artifacts(limit=limit)
    return {"artifacts": items, "count": len(items)}


class PoolDepositRequest(BaseModel):
    amount: float = Field(gt=0)
    reason: str = "sponsor_deposit"


class SurplusRecycleRequest(BaseModel):
    organization_entity_id: str | None = None
    max_providers: int | None = None


@router.get("/balance/summary")
def compute_balance_summary(
    organization_entity_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Utilization, idle providers, pool balance, recycle recommendation."""
    from services.compute_utilization import balance_summary

    org_id = organization_entity_id
    if org_id is None:
        from services.compute_mesh import resolve_org_entity_id

        org_id = resolve_org_entity_id(db, current_user.entity_id)
    return balance_summary(db, organization_entity_id=org_id)


@router.get("/pools/{org_entity_id}")
def get_org_compute_pool(
    org_entity_id: str,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    from services.compute_pool import get_pool_summary

    return get_pool_summary(db, org_entity_id)


@router.post("/pools/{org_entity_id}/deposit")
def deposit_org_compute_pool(
    org_entity_id: str,
    body: PoolDepositRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Sponsor deposits Credits into org compute pool."""
    from models.wallet import CreditTransaction, CreditType, Wallet
    from services.compute_pool import deposit_to_pool

    wallet = db.query(Wallet).filter(Wallet.entity_id == current_user.entity_id).first()
    if wallet is None or wallet.ai_credits < body.amount:
        raise HTTPException(status_code=402, detail="Insufficient AI Credits for pool deposit")
    wallet.ai_credits -= body.amount
    db.add(
        CreditTransaction(
            wallet_id=wallet.id,
            amount=-body.amount,
            credit_type=CreditType.ai_credits,
            reason=f"pool_deposit:{org_entity_id[:8]}",
        )
    )
    summary = deposit_to_pool(
        db,
        org_entity_id,
        body.amount,
        reason=body.reason,
        source_entity_id=current_user.entity_id,
    )
    db.commit()
    return summary


@router.post("/surplus/recycle")
def recycle_surplus_compute(
    body: SurplusRecycleRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Run precompute on idle providers — convert surplus into artifacts."""
    from services.compute_mesh import resolve_org_entity_id
    from services.compute_precompute import recycle_surplus

    org_id = body.organization_entity_id or resolve_org_entity_id(db, current_user.entity_id)
    result = recycle_surplus(
        db,
        organization_entity_id=org_id,
        max_providers=body.max_providers,
    )
    db.commit()
    return result


@router.get("/surplus/idle-providers")
def list_idle_compute_providers(
    organization_entity_id: str | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    from services.compute_mesh import resolve_org_entity_id
    from services.compute_utilization import list_idle_providers

    org_id = organization_entity_id or resolve_org_entity_id(db, current_user.entity_id)
    return {"idle_providers": list_idle_providers(db, organization_entity_id=org_id, limit=limit)}
