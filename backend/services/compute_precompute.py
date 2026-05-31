"""Surplus precompute — convert idle GPU time into ComputeArtifacts (v0.3)."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity
from services.compute_artifact import store_artifact
from services.compute_jobs import create_job_record, update_job_record
from services.compute_metering import estimate_token_usage, provider_credits_for_usage
from services.compute_pool import get_compute_pool, spend_from_pool
from services.compute_profile import get_compute_profile
from services.compute_receipt import build_compute_receipt
from services.compute_utilization import list_idle_providers
from services.ledger_chain import append_ledger_record
from services.protocol_config import get_rewards_config


def _surplus_cfg() -> dict[str, Any]:
    return get_rewards_config().get("compute_surplus") or {}


def default_precompute_tasks() -> list[dict[str, Any]]:
    tasks = _surplus_cfg().get("precompute_tasks")
    if tasks:
        return list(tasks)
    return [
        {
            "type": "artifact_warmup",
            "capability": "llm_inference",
            "model": "surplus-precompute",
            "prompts": [
                "Summarize verified contribution in one sentence.",
                "List three ways distributed compute reduces AI inequality.",
                "Explain PoCP receipt-based settlement briefly.",
            ],
        },
        {
            "type": "embedding_warmup",
            "capability": "embeddings",
            "model": "surplus-embed",
            "texts": ["contribution graph node", "compute provider entity", "witness quorum"],
        },
    ]


def _mock_precompute_output(task_type: str, material: str) -> str:
    if task_type == "embedding_warmup":
        return f"[embedding:{hash(material) % 100000:05d}]"
    return f"[precomputed:{material[:80]}]"


def run_precompute_on_provider(
    db: Session,
    *,
    provider_entity_id: str,
    organization_entity_id: str | None,
    task: dict[str, Any],
    pool_pay: bool = True,
) -> dict[str, Any]:
    task_type = str(task.get("type") or "artifact_warmup")
    capability = str(task.get("capability") or "llm_inference")
    model = str(task.get("model") or "surplus-precompute")
    material_key = "prompts" if task_type == "artifact_warmup" else "texts"
    materials = task.get(material_key) or task.get("prompts") or task.get("texts") or []
    if not materials:
        materials = ["default warmup"]

    results: list[dict[str, Any]] = []
    for material in materials[:3]:
        output = _mock_precompute_output(task_type, str(material))
        artifact = store_artifact(
            model=model,
            input_material=str(material),
            output_material=output,
            provider_entity_id=provider_entity_id,
        )
        usage = estimate_token_usage(prompt=str(material), output=output)
        usage["precompute"] = True
        provider_credit = provider_credits_for_usage(usage, model=model, capability=capability)
        pool_spent = 0.0

        if pool_pay and organization_entity_id:
            pool = get_compute_pool(db, organization_entity_id)
            if float(pool.get("balance_credits") or 0) >= provider_credit:
                spend_from_pool(
                    db,
                    organization_entity_id,
                    provider_credit,
                    reason=f"precompute:{task_type}",
                    beneficiary_entity_id=provider_entity_id,
                )
                pool_spent = provider_credit

        job = create_job_record(
            db,
            capability=capability,
            initiator_entity_id=organization_entity_id,
            contribution_id=None,
            task_id=None,
            constraints={
                "job_kind": "precompute",
                "task_type": task_type,
                "material_preview": str(material)[:200],
            },
            selected_provider={"provider_entity_id": provider_entity_id, "source": "surplus_recycle"},
            receipt=None,
            status="scheduled",
        )
        receipt = build_compute_receipt(
            provider_entity_id=provider_entity_id,
            provider_node_id=os.getenv("POCP_NODE_ID", "local"),
            capability=capability,
            adapter="surplus_precompute",
            model=model,
            job_id=job["job_id"],
            initiator_entity_id=organization_entity_id,
            input_material=str(material)[:2000],
            output_material=output[:2000],
            latency_ms=1,
            extra={
                "execution_mode": "precompute",
                "usage": usage,
                "artifact_ref": {
                    "input_hash": artifact.get("input_hash"),
                    "output_hash": artifact.get("output_hash"),
                },
                "pool_credits_spent": pool_spent,
            },
        )
        update_job_record(
            db,
            job["job_id"],
            status="completed",
            compute_receipt=receipt,
            execution={"task_type": task_type, "precompute": True},
        )
        results.append(
            {
                "job_id": job["job_id"],
                "task_type": task_type,
                "material": str(material)[:80],
                "artifact": artifact,
                "provider_credits": provider_credit,
                "pool_credits_spent": pool_spent,
                "receipt_hash": (receipt.get("integrity") or {}).get("receipt_hash"),
            }
        )

    append_ledger_record(
        db,
        contribution_id=None,
        event_type="compute_surplus_precompute",
        payload={
            "provider_entity_id": provider_entity_id,
            "organization_entity_id": organization_entity_id,
            "task_type": task_type,
            "artifacts_created": len(results),
        },
    )
    return {"provider_entity_id": provider_entity_id, "results": results}


def recycle_surplus(
    db: Session,
    *,
    organization_entity_id: str | None = None,
    max_providers: int | None = None,
    max_tasks_per_provider: int | None = None,
) -> dict[str, Any]:
    cfg = _surplus_cfg()
    if not cfg.get("enabled", True):
        return {"status": "disabled", "recycled": []}

    max_providers = max_providers or int(cfg.get("max_providers_per_cycle") or 3)
    max_tasks = max_tasks_per_provider or int(cfg.get("max_precompute_per_cycle") or 2)
    idle = list_idle_providers(db, organization_entity_id=organization_entity_id, limit=max_providers)
    tasks = default_precompute_tasks()[:max_tasks]

    recycled: list[dict[str, Any]] = []
    for item in idle:
        provider_id = item["provider_entity_id"]
        entity = db.get(Entity, provider_id)
        profile = get_compute_profile(entity) if entity else {}
        org_id = organization_entity_id or (profile.get("policy") or {}).get("organization_entity_id")
        for task in tasks:
            recycled.append(
                run_precompute_on_provider(
                    db,
                    provider_entity_id=provider_id,
                    organization_entity_id=org_id,
                    task=task,
                    pool_pay=bool(org_id),
                )
            )

    if organization_entity_id and recycled:
        org = db.get(Entity, organization_entity_id)
        if org:
            meta = dict(org.metadata_ or {})
            pool = meta.get("compute_pool") or {}
            pool["precompute_runs"] = int(pool.get("precompute_runs") or 0) + len(recycled)
            meta["compute_pool"] = pool
            org.metadata_ = meta
            db.flush()

    return {
        "status": "completed",
        "idle_providers_found": len(idle),
        "providers_recycled": len(recycled),
        "artifacts_hint": "stored via ComputeArtifact; use cache_hit on matching prompts",
        "recycled": recycled,
    }
