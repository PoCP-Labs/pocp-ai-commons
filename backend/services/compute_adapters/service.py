"""Orchestrate external compute adapters with PoCP job store and receipts."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.entity import Entity, EntityStatus, EntityType
from services.compute_adapters.base import AdapterJobSpec, AdapterJobStatus
from services.compute_adapters.live_config import adapter_runtime_status
from services.compute_adapters.registry import get_adapter, list_adapters
from services.compute_jobs import create_job_record, get_job_record, update_job_record
from services.compute_profile import get_compute_profile, register_compute_profile
from services.compute_receipt import build_compute_receipt
from services.compute_settlement import settle_bilateral


def list_adapter_catalog() -> dict[str, Any]:
    adapters = []
    for entry in list_adapters():
        runtime = adapter_runtime_status(entry["slug"], default=entry.get("mode", "stub"))
        adapters.append({**entry, **runtime})
    return {
        "spec_version": "pocp.compute_adapter.v0.1",
        "adapters": adapters,
        "principle": "External network tokens are evidence only — not PoCP CP issuance.",
        "spec_doc": "docs/COMPUTE-ADAPTER-SPEC.md",
        "live_wire_doc": "docs/COMPUTE-ADAPTER-LIVE-WIRE.md",
    }


def import_adapter_provider(
    db: Session,
    slug: str,
    manifest: dict[str, Any],
    *,
    owner_entity_id: str,
) -> dict[str, Any]:
    adapter = get_adapter(slug)
    display_name = str(manifest.get("display_name") or adapter.display_name).strip()
    entity_id = str(manifest.get("entity_id") or f"pocp-adapt-{slug[:6]}-{uuid.uuid4().hex[:8]}")
    if len(entity_id) > 36:
        raise ValueError("entity_id must be at most 36 characters")

    entity = db.get(Entity, entity_id)
    if entity is None:
        entity = Entity(
            id=entity_id,
            entity_type=EntityType.community,
            name=display_name[:255],
            description=str(manifest.get("summary") or f"External compute via {adapter.display_name}")[:500],
            status=EntityStatus.active,
            owner_id=owner_entity_id,
        )
        db.add(entity)
    else:
        entity.name = display_name[:255]

    offers = manifest.get("offers") or [
        {
            "capability": "llm_inference",
            "adapters": [adapter.slug],
            "models": list(manifest.get("models") or []),
        }
    ]
    for offer in offers:
        adapters = offer.get("adapters") or []
        if adapter.slug not in adapters:
            offer["adapters"] = [adapter.slug, *adapters]

    profile_payload = {
        "offers": offers,
        "endpoints": manifest.get("endpoints") or {},
        "capacity": manifest.get("capacity") or {},
        "policy": manifest.get("policy") or {"accepts_public_jobs": False},
        "accountability": {"owner_entity_id": owner_entity_id},
        "status": manifest.get("status") or "active",
    }
    register_compute_profile(db, entity_id, profile_payload, owner_entity_id=owner_entity_id)

    meta = dict(entity.metadata_ or {})
    meta["compute_adapter"] = {
        "slug": adapter.slug,
        "mode": adapter.mode,
        "network": adapter.network,
        "external_provider_id": manifest.get("external_provider_id"),
        "external": manifest.get("external") or {},
        "inspiration_slug": adapter.inspiration_slug,
    }
    meta["roles"] = sorted(set([*(meta.get("roles") or []), "compute_provider", "external_adapter"]))
    entity.metadata_ = meta
    db.flush()

    return {
        "entity_id": entity_id,
        "adapter": adapter.catalog_entry(),
        "compute_profile": get_compute_profile(entity),
        "imported": True,
    }


def submit_adapter_job(
    db: Session,
    slug: str,
    *,
    capability: str,
    requester_entity_id: str,
    provider_entity_id: str,
    contribution_id: str | None = None,
    task_id: str | None = None,
    trace_id: str | None = None,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    adapter = get_adapter(slug)
    provider = db.get(Entity, provider_entity_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider entity not found")

    adapter_meta = (provider.metadata_ or {}).get("compute_adapter") or {}
    if adapter_meta.get("slug") and adapter_meta.get("slug") != adapter.slug:
        raise HTTPException(
            status_code=400,
            detail=f"Provider entity is registered for adapter {adapter_meta.get('slug')}, not {adapter.slug}",
        )

    spec = AdapterJobSpec(
        capability=capability,
        requester_entity_id=requester_entity_id,
        provider_entity_id=provider_entity_id,
        contribution_id=contribution_id,
        task_id=task_id,
        trace_id=trace_id,
        constraints=constraints or {},
    )
    try:
        spec.validate()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    quote = adapter.quote_job(spec)
    submit = adapter.submit_job(spec)
    started_at = datetime.now(timezone.utc)

    receipt_stub = build_compute_receipt(
        provider_entity_id=provider_entity_id,
        provider_node_id=None,
        capability=capability,
        adapter=adapter.slug,
        model=spec.constraints.get("model"),
        contribution_id=contribution_id,
        task_id=task_id,
        initiator_entity_id=requester_entity_id,
        input_material=spec.constraints.get("input_preview"),
        started_at=started_at,
        extra={
            "external_job_id": submit.external_job_id,
            "adapter_mode": adapter.mode,
            "status": submit.status.value,
            "quote": quote,
        },
    )

    job = create_job_record(
        db,
        capability=capability,
        initiator_entity_id=requester_entity_id,
        contribution_id=contribution_id,
        task_id=task_id,
        constraints=constraints or {},
        selected_provider={
            "source": "external_adapter",
            "adapter": adapter.slug,
            "provider_entity_id": provider_entity_id,
            "network": adapter.network,
            "mode": adapter.effective_mode(),
        },
        receipt=receipt_stub,
        status="scheduled",
    )

    update_job_record(
        db,
        job["job_id"],
        execution={
            "external_job_id": submit.external_job_id,
            "adapter": adapter.slug,
            "started_at": started_at.isoformat(),
            "poll_count": 0,
            "adapter_spec": {
                "capability": capability,
                "provider_entity_id": provider_entity_id,
                "contribution_id": contribution_id,
                "task_id": task_id,
                "trace_id": trace_id,
                "constraints": constraints or {},
            },
        },
    )
    return get_job_record(db, job["job_id"])


def poll_adapter_job(db: Session, slug: str, job_id: str) -> dict[str, Any]:
    adapter = get_adapter(slug)
    job = get_job_record(db, job_id)
    execution = job.get("execution") or {}
    if execution.get("adapter") and execution.get("adapter") != adapter.slug:
        raise HTTPException(status_code=400, detail="Job belongs to a different adapter")

    external_job_id = execution.get("external_job_id")
    if not external_job_id:
        raise HTTPException(status_code=400, detail="Job has no external_job_id")

    spec_data = execution.get("adapter_spec") or {}
    spec = AdapterJobSpec(
        capability=job.get("capability") or spec_data.get("capability") or "llm_inference",
        requester_entity_id=job.get("initiator_entity_id") or "",
        provider_entity_id=(job.get("selected_provider") or {}).get("provider_entity_id")
        or spec_data.get("provider_entity_id")
        or "",
        contribution_id=job.get("contribution_id"),
        task_id=job.get("task_id"),
        trace_id=spec_data.get("trace_id"),
        constraints=spec_data.get("constraints") or {},
    )

    poll = adapter.poll_job(external_job_id, context=execution)
    poll_count = int(execution.get("poll_count") or 0) + 1
    execution = {
        **execution,
        "poll_count": poll_count,
        "last_poll_status": poll.status.value,
        "last_polled_at": datetime.now(timezone.utc).isoformat(),
    }

    if poll.status == AdapterJobStatus.failed:
        update_job_record(
            db,
            job_id,
            status="failed",
            execution={**execution, "failure": adapter.map_failure(poll.error or "poll failed")},
        )
        return get_job_record(db, job_id)

    if poll.status in (AdapterJobStatus.queued, AdapterJobStatus.running):
        update_job_record(db, job_id, execution=execution)
        return get_job_record(db, job_id)

    started_text = execution.get("started_at")
    started_at = datetime.fromisoformat(started_text.replace("Z", "+00:00")) if started_text else None
    receipt = adapter.build_receipt(
        spec,
        external_job_id=external_job_id,
        poll=poll,
        job_id=job_id,
        started_at=started_at,
        input_material=spec.constraints.get("input_preview"),
    )
    settlement = settle_bilateral(
        db,
        receipt,
        consumer_entity_id=job.get("initiator_entity_id"),
    )
    if settlement:
        receipt["settlement"] = settlement

    update_job_record(
        db,
        job_id,
        status="completed",
        compute_receipt=receipt,
        execution={**execution, "completed": True},
        settlement=settlement,
    )
    return get_job_record(db, job_id)
