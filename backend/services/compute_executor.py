"""Execute scheduled compute jobs — bridge scheduler → inference / witness."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from services.ai_chat import generate_ai_reply
from services.compute_artifact import lookup_artifact, store_artifact
from services.compute_jobs import get_job_record, update_job_record
from services.compute_metering import estimate_token_usage, usage_from_adapter
from services.compute_receipt import build_compute_receipt
from services.compute_scheduler import ComputeJob, schedule_compute_job
from services.federation_settlement import settle_compute_receipt
from services.intel_receipt import build_intel_receipt
from services.ollama_client import ollama_base_url, ollama_chat_model
from services.remote_witness import run_witness


async def begin_llm_job(
    db: Session,
    *,
    human_entity_id: str,
    contribution_id: str | None,
    task_id: str | None,
    provider: str,
    model: str | None,
    prompt: str,
) -> tuple[str | None, dict[str, Any] | None]:
    """Schedule llm_inference and return (job_id, preliminary receipt)."""
    result = schedule_compute_job(
        db,
        ComputeJob(
            capability="llm_inference",
            initiator_entity_id=human_entity_id,
            contribution_id=contribution_id,
            task_id=task_id,
            constraints={
                "model": model,
                "provider": provider,
                "input_preview": prompt[:500],
            },
        ),
    )
    if result.get("status") == "no_provider":
        return None, None
    return result.get("job_id"), result.get("compute_receipt")


async def _execute_openai_compatible_llm(
    *,
    base_url: str,
    prompt: str,
    system: str,
    model: str | None,
    adapter: str | None,
) -> tuple[str, str, str, dict[str, Any]]:
    root = base_url.rstrip("/")
    adapter = (adapter or "openai").lower()
    timeout = float(os.getenv("POCP_REMOTE_LLM_TIMEOUT", "120"))

    if adapter == "ollama":
        model_name = model or ollama_chat_model()
        chat_url = f"{root}/api/chat"
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                chat_url,
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                },
            )
            resp.raise_for_status()
            content = (resp.json().get("message") or {}).get("content") or ""
            usage = estimate_token_usage(prompt=prompt, output=content, system=system)
            return content, "ollama", model_name, usage

    model_name = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("REMOTE_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{root}/v1/chat/completions",
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
            },
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = usage_from_adapter(data.get("usage"), prompt=prompt, output=content, system=system)
        return content, adapter, model_name, usage


async def execute_llm_inference(
    db: Session,
    *,
    human_entity_id: str,
    contribution_id: str | None,
    task_id: str | None,
    provider: str,
    model: str | None,
    prompt: str,
    system_content: str,
    skill_entity_id: str | None = None,
) -> tuple[str, str, str, dict[str, Any] | None, dict[str, Any]]:
    """Schedule, execute (local / remote Entity / fallback), settle, return receipt."""
    job_id, schedule_receipt = await begin_llm_job(
        db,
        human_entity_id=human_entity_id,
        contribution_id=contribution_id,
        task_id=task_id,
        provider=provider,
        model=model,
        prompt=prompt,
    )
    selected: dict[str, Any] = {}
    if job_id:
        selected = get_job_record(db, job_id).get("selected_provider") or {}

    started_ms = time.time() * 1000
    effective_provider = provider
    if selected.get("adapter") and selected.get("adapter") not in ("local", "local_node"):
        effective_provider = str(selected["adapter"]).lower()
    if selected.get("model"):
        model = selected.get("model")

    remote_base = selected.get("base_url")
    source = selected.get("source")
    execution_mode = "live_inference"
    usage: dict[str, Any] | None = None
    artifact_ref: dict[str, Any] | None = None

    effective_model = model or ""
    cached = lookup_artifact(model=effective_model or "mock-chat", input_material=prompt)
    if cached:
        output = str(cached.get("output_material") or "")
        effective_provider = provider
        model = effective_model or "mock-chat"
        execution_mode = "cache_hit"
        artifact_ref = cached
        usage = estimate_token_usage(prompt=prompt, output=output, system=system_content)
    else:
        try:
            if source == "peer_node" and remote_base:
                output, effective_provider, model, usage = await _execute_peer_inference(
                    base_url=remote_base,
                    prompt=prompt,
                    system=system_content,
                    provider=effective_provider,
                    model=model,
                )
            elif source == "entity" and remote_base and remote_base.rstrip("/") != os.getenv(
                "BACKEND_URL", "http://127.0.0.1:8000"
            ).rstrip("/"):
                output, effective_provider, model, usage = await _execute_openai_compatible_llm(
                    base_url=remote_base,
                    prompt=prompt,
                    system=system_content,
                    model=model,
                    adapter=effective_provider,
                )
            else:
                output, effective_provider, model = await generate_ai_reply(
                    prompt,
                    provider=effective_provider,
                    model=model,
                    system_content=system_content,
                )
                usage = estimate_token_usage(
                    prompt=prompt, output=output, system=system_content
                )
        except Exception as exc:
            output, effective_provider, model = await generate_ai_reply(
                prompt,
                provider=provider,
                model=model,
                system_content=system_content,
            )
            usage = estimate_token_usage(prompt=prompt, output=output, system=system_content)
            if selected:
                selected = {**selected, "fallback": str(exc)[:200]}

        if execution_mode == "live_inference":
            store_artifact(
                model=model or "",
                input_material=prompt,
                output_material=output,
                provider_entity_id=selected.get("provider_entity_id"),
            )

    receipt = complete_llm_job(
        db,
        job_id,
        provider=effective_provider,
        model=model or "",
        prompt=prompt,
        output=output,
        started_ms=started_ms,
        selected_provider=selected or None,
        consumer_entity_id=human_entity_id,
        usage=usage,
        execution_mode=execution_mode,
        artifact_ref=artifact_ref,
        skill_entity_id=skill_entity_id,
    )
    meta = {
        "job_id": job_id,
        "selected_provider": selected,
        "schedule_receipt": schedule_receipt,
    }
    return output, effective_provider, model or "", receipt, meta


def complete_llm_job(
    db: Session | None,
    job_id: str | None,
    *,
    provider: str,
    model: str,
    prompt: str,
    output: str,
    started_ms: float,
    selected_provider: dict[str, Any] | None = None,
    consumer_entity_id: str | None = None,
    usage: dict[str, Any] | None = None,
    execution_mode: str = "live_inference",
    artifact_ref: dict[str, Any] | None = None,
    skill_entity_id: str | None = None,
) -> dict[str, Any] | None:
    if not job_id:
        return None
    latency = int(max(time.time() * 1000 - started_ms, 0))
    job = get_job_record(db, job_id)
    sel = selected_provider or job.get("selected_provider") or {}
    if usage is None:
        usage = estimate_token_usage(prompt=prompt, output=output)
    extra: dict[str, Any] = {
        "source": sel.get("source"),
        "base_url": sel.get("base_url"),
        "executed_remotely": sel.get("source") in ("entity", "peer_node")
        and sel.get("base_url")
        and not sel.get("fallback"),
        "fallback": sel.get("fallback"),
        "usage": usage,
        "execution_mode": execution_mode,
    }
    if artifact_ref:
        extra["artifact_ref"] = {
            "input_hash": artifact_ref.get("input_hash"),
            "output_hash": artifact_ref.get("output_hash"),
            "stored_at": artifact_ref.get("stored_at"),
        }
    receipt = build_compute_receipt(
        provider_entity_id=sel.get("provider_entity_id"),
        provider_node_id=sel.get("provider_node_id"),
        capability="llm_inference",
        adapter=provider,
        model=model,
        contribution_id=job.get("contribution_id"),
        task_id=job.get("task_id"),
        job_id=job_id,
        initiator_entity_id=job.get("initiator_entity_id"),
        input_material=prompt[:2000],
        output_material=output[:2000],
        latency_ms=latency,
        extra=extra,
    )
    settlement = None
    if db is not None:
        settlement = settle_compute_receipt(
            db,
            receipt,
            consumer_entity_id=consumer_entity_id or job.get("initiator_entity_id"),
            selected_provider=sel or None,
            skill_entity_id=skill_entity_id,
        )
        if settlement:
            receipt["settlement"] = settlement

    update_job_record(
        db,
        job_id,
        status="completed",
        compute_receipt=receipt,
        execution={"provider": provider, "model": model},
        settlement=settlement,
    )
    return receipt


async def begin_witness_job(
    db: Session,
    *,
    contribution_id: str,
    initiator_entity_id: str | None,
    context_preview: str,
) -> dict[str, Any]:
    """Schedule witness capability for auto-verify; returns full schedule result."""
    return schedule_compute_job(
        db,
        ComputeJob(
            capability="witness",
            initiator_entity_id=initiator_entity_id,
            contribution_id=contribution_id,
            constraints={"input_preview": context_preview[:500]},
        ),
    )


async def execute_compute_job(
    db: Session, job_id: str, *, context: dict | None = None
) -> dict[str, Any]:
    """Run a scheduled job (witness or llm_inference advisory execution)."""
    job = get_job_record(db, job_id)
    capability = job.get("capability")
    selected = job.get("selected_provider") or {}
    started_ms = time.time() * 1000

    if capability == "witness":
        provider = selected.get("adapter") or "mock"
        if selected.get("source") == "peer_node" and selected.get("base_url"):
            result = await _execute_peer_witness(
                base_url=selected["base_url"],
                context=context or {},
                provider=provider,
            )
        else:
            result = await run_witness(context or {}, provider=provider)
        payload = result.model_dump() if hasattr(result, "model_dump") else dict(result)
        from services.compute_metering import intel_usage_for_service

        witness_usage = intel_usage_for_service("witness")
        witness_usage["service"] = "witness"
        receipt = build_compute_receipt(
            provider_entity_id=selected.get("provider_entity_id"),
            provider_node_id=selected.get("provider_node_id"),
            capability="witness",
            adapter=provider,
            contribution_id=job.get("contribution_id"),
            task_id=job.get("task_id"),
            job_id=job_id,
            initiator_entity_id=job.get("initiator_entity_id"),
            input_material=str(context)[:2000] if context else None,
            output_material=str(payload)[:2000],
            latency_ms=int(time.time() * 1000 - started_ms),
            extra={"source": selected.get("source"), "executed": True, "usage": witness_usage},
        )
        intel_receipt = None
        if selected.get("provider_entity_id"):
            intel_receipt = build_intel_receipt(
                provider_entity_id=selected["provider_entity_id"],
                service="witness",
                contribution_id=job.get("contribution_id"),
                task_id=job.get("task_id"),
                initiator_entity_id=job.get("initiator_entity_id"),
                downstream_compute_receipt_hashes=[
                    (receipt.get("integrity") or {}).get("receipt_hash")
                ],
            )
        settlement = settle_compute_receipt(
            db,
            receipt,
            consumer_entity_id=job.get("initiator_entity_id"),
            selected_provider=selected or None,
        )
        if settlement and settlement.get("settled") and intel_receipt:
            intel_receipt["settlement"] = settlement
        if settlement:
            receipt["settlement"] = settlement
        update_job_record(
            db,
            job_id,
            status="completed",
            compute_receipt=receipt,
            execution=payload,
            settlement=settlement,
        )
        return {
            **job,
            "status": "completed",
            "compute_receipt": receipt,
            "intel_receipt": intel_receipt,
            "execution": payload,
        }

    if capability == "llm_inference":
        raise HTTPException(
            status_code=400,
            detail="llm_inference jobs execute via execute_llm_inference; use complete_llm_job",
        )

    raise HTTPException(status_code=400, detail=f"Unsupported capability for execute: {capability}")


async def _execute_peer_inference(
    *,
    base_url: str,
    prompt: str,
    system: str,
    provider: str,
    model: str | None,
) -> tuple[str, str, str, dict[str, Any]]:
    from services.peer_trust import build_peer_auth_headers

    url = f"{base_url.rstrip('/')}/api/v1/intelligence/compute/inference"
    headers = {"Content-Type": "application/json"}
    headers.update(build_peer_auth_headers())
    async with httpx.AsyncClient(timeout=float(os.getenv("POCP_REMOTE_LLM_TIMEOUT", "120"))) as client:
        resp = await client.post(
            url,
            json={
                "prompt": prompt,
                "system_content": system,
                "provider": provider,
                "model": model,
            },
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        output = str(data.get("output") or "")
        prov = str(data.get("provider") or provider)
        mdl = str(data.get("model") or model or "")
        usage = usage_from_adapter(data.get("usage"), prompt=prompt, output=output, system=system)
        return output, prov, mdl, usage


async def _execute_peer_witness(base_url: str, context: dict, provider: str) -> Any:
    from services.peer_trust import build_peer_auth_headers
    from services.verifiers.base import VerifierResult

    url = f"{base_url.rstrip('/')}/api/v1/intelligence/compute/witness"
    headers = {"Content-Type": "application/json"}
    headers.update(build_peer_auth_headers())
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                url,
                json={"context": context, "provider": provider},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            inner = data.get("result") or data
            return VerifierResult(**inner) if isinstance(inner, dict) and "provider" in inner else inner
    except Exception:
        return await run_witness(context, provider=provider)
