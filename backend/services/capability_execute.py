"""Execute registered Skills and Agents — native LLM, optional OpenClaw gateway."""

from __future__ import annotations

import hashlib
import os
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from genesis import LUMEN_0_ID
from models.ai_usage import AIUsageLog
from models.agent import Agent
from models.entity import Entity, EntityStatus, EntityType
from models.invocation import InvocationStatus, InvocationStep, InvocationTrace
from models.skill import Skill
from models.wallet import CreditTransaction, CreditType, Wallet
from services.agent_receipt import build_agent_receipt
from services.ai_chat import AI_CHAT_COST_PER_MESSAGE
from services.compute_metering import burn_tokens_from_receipt, settlement_block
from services.compute_settlement import settle_intel_provider
from services.intel_receipt import build_intel_receipt
from services.anti_abuse import check_daily_ai_burn_limit
from services.exchange_spine import emit_exchange_settled
from services.ledger_chain import append_ledger_record

SKILL_EXECUTE_COST = float(os.getenv("SKILL_EXECUTE_COST", str(AI_CHAT_COST_PER_MESSAGE)))
AGENT_EXECUTE_COST = float(os.getenv("AGENT_EXECUTE_COST", str(AI_CHAT_COST_PER_MESSAGE)))


def _require_human(db: Session, entity_id: str) -> Entity:
    entity = db.get(Entity, entity_id)
    if not entity or entity.entity_type != EntityType.human:
        raise HTTPException(status_code=400, detail="Initiator must be a human entity")
    return entity


def _require_executable_entity(db: Session, entity_id: str, expected: EntityType) -> Entity:
    entity = db.get(Entity, entity_id)
    if not entity or entity.entity_type != expected:
        raise HTTPException(status_code=404, detail=f"{expected.value.title()} entity not found")
    if entity.status != EntityStatus.active:
        raise HTTPException(
            status_code=400,
            detail=f"{expected.value.title()} must be active before execution (current: {entity.status.value})",
        )
    return entity


def _resolve_llm_entity(db: Session, llm_entity_id: str | None) -> Entity:
    entity = db.get(Entity, llm_entity_id or LUMEN_0_ID)
    if not entity or entity.entity_type != EntityType.llm:
        raise HTTPException(status_code=404, detail="LLM entity not found")
    return entity


def _runtime_mode(entity: Entity) -> str:
    runtime = (entity.metadata_ or {}).get("runtime") or {}
    if runtime.get("mode"):
        return str(runtime["mode"])
    if runtime.get("gateway") or runtime.get("openclaw_gateway"):
        return "openclaw"
    return "native"


async def _burn_credits_for_execution(
    db: Session,
    *,
    entity_id: str,
    prompt: str,
    response: str,
    provider: str,
    model: str,
    cost: float,
    reason: str,
    provider_entity_id: str | None = None,
    capability: str = "skill_invocation",
    receipt_hash: str | None = None,
) -> dict[str, Any]:
    wallet = db.query(Wallet).filter(Wallet.entity_id == entity_id).first()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    check_daily_ai_burn_limit(db, entity_id, cost)
    if wallet.ai_credits < cost:
        raise HTTPException(status_code=402, detail="Insufficient AI Credits")

    wallet.ai_credits -= cost
    burn_tx = CreditTransaction(
        wallet_id=wallet.id,
        amount=-cost,
        credit_type=CreditType.ai_credits,
        reason=reason,
    )
    db.add(burn_tx)
    db.add(
        AIUsageLog(
            entity_id=entity_id,
            wallet_id=wallet.id,
            provider=provider,
            model=model,
            prompt=prompt[:4000],
            response=response[:4000],
            credits_spent=cost,
        )
    )
    append_ledger_record(
        db,
        contribution_id=None,
        event_type="ai_credits_burned",
        payload={
            "entity_id": entity_id,
            "wallet_id": wallet.id,
            "provider": provider,
            "model": model,
            "credits_spent": cost,
            "pocp_tokens_spent": cost,
            "remaining_credits": wallet.ai_credits,
            "remaining_tokens": wallet.ai_credits,
            "reason": reason,
        },
    )
    provider_ids = [provider_entity_id or os.getenv("POCP_CHAT_PROVIDER_ENTITY_ID", LUMEN_0_ID)]
    if not receipt_hash:
        material = f"{entity_id}|{provider}|{model}|{cost}|{reason}"
        receipt_hash = f"sha256:{hashlib.sha256(material.encode()).hexdigest()}"
    exchange_record = emit_exchange_settled(
        db,
        consumer_entity_id=entity_id,
        provider_entity_ids=provider_ids,
        exchange_kind="capability",
        credit_transactions=[burn_tx],
        receipt_hash=receipt_hash,
        capability=capability,
        usage={
            "metering_mode": "flat",
            "bc_debited": cost,
            "provider": provider,
            "model": model,
        },
        legacy_event_type="ai_credits_burned",
        settlement_policy="capability_execute.v1",
    )
    db.flush()
    return {
        "credits_spent": cost,
        "remaining_credits": wallet.ai_credits,
        "provider": provider,
        "model": model,
        "exchange_id": (exchange_record.payload or {}).get("exchange_id"),
    }


def _record_trace(
    db: Session,
    *,
    human_id: str,
    model_provider: str,
    chain: list[tuple[str, str, str]],
    task_id: str | None,
    contribution_id: str | None,
    step_metadata: list[dict | None] | None = None,
) -> InvocationTrace:
    trace = InvocationTrace(
        initiator_id=human_id,
        task_id=task_id,
        contribution_id=contribution_id,
        model_provider=model_provider,
        status=InvocationStatus.completed,
    )
    db.add(trace)
    db.flush()
    meta_list = step_metadata or [None] * len(chain)
    for order, (source_id, target_id, action) in enumerate(chain, start=1):
        step_meta = meta_list[order - 1] if order - 1 < len(meta_list) else None
        db.add(
            InvocationStep(
                trace_id=trace.id,
                step_order=order,
                source_entity_id=source_id,
                target_entity_id=target_id,
                action=action,
                metadata_=step_meta,
            )
        )
    db.flush()
    return trace


def _load_trace(db: Session, trace_id: str) -> InvocationTrace:
    trace = (
        db.query(InvocationTrace)
        .options(joinedload(InvocationTrace.steps))
        .filter(InvocationTrace.id == trace_id)
        .first()
    )
    if not trace:
        raise HTTPException(status_code=404, detail="Invocation trace not found")
    return trace


def _build_skill_prompt(skill: Skill | None, skill_entity: Entity, user_input: str, context: dict | None) -> str:
    instructions = (skill.prompt_template if skill and skill.prompt_template else skill_entity.description) or ""
    ctx = context or {}
    parts = [
        f"# Skill: {skill_entity.name}",
        instructions.strip(),
        "## User input",
        user_input.strip(),
    ]
    if ctx:
        parts.extend(["## Context", str(ctx)])
    return "\n\n".join(p for p in parts if p)


async def _execute_openclaw_skill(
    *,
    runtime: dict[str, Any],
    skill_name: str,
    user_input: str,
    context: dict | None,
) -> tuple[str, str, str]:
    gateway = (runtime.get("gateway") or runtime.get("openclaw_gateway") or "").rstrip("/")
    if not gateway:
        raise HTTPException(status_code=400, detail="OpenClaw runtime requires gateway URL")

    execute_url = runtime.get("execute_url") or f"{gateway}/api/v1/skills/{skill_name}/execute"
    payload = {"input": user_input, "context": context or {}}
    headers = {}
    if runtime.get("api_key"):
        headers["Authorization"] = f"Bearer {runtime['api_key']}"

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(execute_url, json=payload, headers=headers)
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"OpenClaw gateway error ({resp.status_code}): {resp.text[:300]}",
            )
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        output = data.get("output") or data.get("result") or data.get("content") or resp.text
        return str(output), "openclaw", skill_name


async def execute_skill(
    db: Session,
    *,
    human_entity_id: str,
    skill_entity_id: str,
    user_input: str,
    context: dict[str, Any] | None = None,
    agent_entity_id: str | None = None,
    llm_entity_id: str | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    task_id: str | None = None,
    contribution_id: str | None = None,
) -> dict[str, Any]:
    """Run a registered Skill entity and record Human → [Agent] → Skill → LLM invocation."""
    _require_human(db, human_entity_id)
    skill_entity = _require_executable_entity(db, skill_entity_id, EntityType.skill)
    llm_entity = _resolve_llm_entity(db, llm_entity_id)
    skill_row = db.query(Skill).filter(Skill.entity_id == skill_entity.id).first()

    agent_entity: Entity | None = None
    if agent_entity_id:
        agent_entity = _require_executable_entity(db, agent_entity_id, EntityType.agent)

    runtime = (skill_entity.metadata_ or {}).get("runtime") or {}
    mode = _runtime_mode(skill_entity)
    meta = skill_entity.metadata_ or {}
    skill_name = meta.get("capability_external_id") or skill_entity.name

    system = (
        f"You are executing the PoCP skill '{skill_entity.name}'. "
        "Follow the skill instructions precisely. Output should be suitable for human review."
    )
    prompt = _build_skill_prompt(skill_row, skill_entity, user_input, context)

    compute_receipt = None
    job_id = None
    schedule_receipt = None
    selected: dict[str, Any] = {}
    skill_settlement = None
    intel_receipt = None
    if mode == "openclaw":
        output, provider, model = await _execute_openclaw_skill(
            runtime=runtime,
            skill_name=str(skill_name),
            user_input=user_input,
            context=context,
        )
        billing = {"credits_spent": 0.0, "remaining_credits": None, "provider": provider, "model": model}
    else:
        provider = (llm_provider or runtime.get("llm_provider") or os.getenv("SKILL_LLM_PROVIDER", "mock")).lower()
        model = llm_model or runtime.get("llm_model")
        from services.compute_executor import execute_llm_inference

        output, provider, model, compute_receipt, compute_meta = await execute_llm_inference(
            db,
            human_entity_id=human_entity_id,
            contribution_id=contribution_id,
            task_id=task_id,
            provider=provider,
            model=model,
            prompt=prompt,
            system_content=system,
            skill_entity_id=skill_entity.id,
        )
        job_id = compute_meta.get("job_id")
        schedule_receipt = compute_meta.get("schedule_receipt")
        selected = compute_meta.get("selected_provider") or {}
        wallet = db.query(Wallet).filter(Wallet.entity_id == human_entity_id).first()
        compute_settlement = (compute_receipt or {}).get("settlement") or {}
        if compute_settlement.get("settled") and compute_settlement.get("consumer_debited"):
            billing = {
                "credits_spent": compute_settlement.get("consumer_tokens", 0),
                "remaining_credits": compute_settlement.get("consumer_remaining_tokens"),
                "provider": provider,
                "model": model,
                "settlement": (
                    "skill_orchestration_split"
                    if compute_settlement.get("multiparty_split")
                    else "bilateral_compute"
                ),
            }
        else:
            receipt_hash = (compute_receipt.get("integrity") or {}).get("receipt_hash") if compute_receipt else None
            billing = await _burn_credits_for_execution(
                db,
                entity_id=human_entity_id,
                prompt=prompt,
                response=output,
                provider=provider,
                model=model,
                cost=burn_tokens_from_receipt(compute_receipt) if compute_receipt else SKILL_EXECUTE_COST,
                reason=f"Skill execution: {skill_entity.name}",
                provider_entity_id=skill_entity.id,
                capability="skill_invocation",
                receipt_hash=receipt_hash,
            )
        if wallet and billing.get("remaining_credits") is None:
            billing["remaining_credits"] = wallet.ai_credits

        if compute_settlement.get("multiparty_split"):
            receipt_hash = (compute_receipt.get("integrity") or {}).get("receipt_hash")
            intel_receipt = build_intel_receipt(
                provider_entity_id=skill_entity.id,
                service="skill_orchestration",
                contribution_id=contribution_id,
                task_id=task_id,
                initiator_entity_id=human_entity_id,
                downstream_compute_receipt_hashes=[receipt_hash] if receipt_hash else [],
                extra={
                    "split": compute_settlement.get("split"),
                    "settlement": compute_settlement.get("settlement"),
                },
            )
            if compute_settlement.get("settled"):
                intel_receipt["settlement"] = {
                    "skill_credits_granted": compute_settlement.get("skill_credits_granted"),
                    "protocol_fee_collected": compute_settlement.get("protocol_fee_collected"),
                    "split": compute_settlement.get("split"),
                }
            skill_settlement = compute_settlement
        elif compute_settlement.get("settled"):
            skill_settlement = settle_intel_provider(
                db,
                provider_entity_id=skill_entity.id,
                service="skill_invocation",
                consumer_entity_id=human_entity_id,
                contribution_id=contribution_id,
                task_id=task_id,
            )

    chain: list[tuple[str, str, str]] = []
    step_meta: list[dict | None] = []
    if agent_entity:
        chain.append((human_entity_id, agent_entity.id, "uses"))
        step_meta.append(None)
        chain.append((agent_entity.id, skill_entity.id, "calls"))
        step_meta.append({"capability_kind": "skill", "skill_name": skill_entity.name})
    else:
        chain.append((human_entity_id, skill_entity.id, "uses"))
        step_meta.append({"capability_kind": "skill", "skill_name": skill_entity.name})
    chain.append((skill_entity.id, llm_entity.id, "invokes_llm"))
    llm_meta: dict[str, Any] = {"capability_kind": "llm", "provider": provider, "model": model}
    if mode != "openclaw" and compute_receipt:
        llm_meta["compute_receipt"] = compute_receipt
    step_meta.append(llm_meta)

    trace = _record_trace(
        db,
        human_id=human_entity_id,
        model_provider=provider,
        chain=chain,
        task_id=task_id,
        contribution_id=contribution_id,
        step_metadata=step_meta,
    )
    trace_loaded = _load_trace(db, trace.id)

    return {
        "execution_type": "skill",
        "mode": mode,
        "skill_entity_id": skill_entity.id,
        "skill_name": skill_entity.name,
        "agent_entity_id": agent_entity.id if agent_entity else None,
        "llm_entity_id": llm_entity.id,
        "trace_id": trace.id,
        "output": output,
        "billing": billing,
        "invocation_chain": [
            {
                "step_order": step.step_order,
                "source_entity_id": step.source_entity_id,
                "target_entity_id": step.target_entity_id,
                "action": step.action,
            }
            for step in sorted(trace_loaded.steps, key=lambda s: s.step_order)
        ],
        "receipt_url": f"/api/v1/invocations/{trace.id}/receipt",
        "compute_job_id": job_id if mode != "openclaw" else None,
        "compute_receipt": compute_receipt if mode != "openclaw" else None,
        "compute_schedule": schedule_receipt if mode != "openclaw" else None,
        "selected_provider": selected if mode != "openclaw" else None,
        "skill_settlement": skill_settlement,
        "intel_receipt": intel_receipt if mode != "openclaw" else None,
        "advisory_only": True,
        "note": "Output is advisory; attach trace_id to contribution evidence for verification.",
    }


async def execute_agent(
    db: Session,
    *,
    human_entity_id: str,
    agent_entity_id: str,
    user_input: str,
    context: dict[str, Any] | None = None,
    skill_entity_id: str | None = None,
    task_id: str | None = None,
    contribution_id: str | None = None,
    llm_entity_id: str | None = None,
    llm_provider: str | None = None,
    submit_contribution: bool = False,
) -> dict[str, Any]:
    """Execute an Agent entity — StudyAgent graph or generic agent+skill orchestration."""
    agent_entity = _require_executable_entity(db, agent_entity_id, EntityType.agent)
    agent_row = db.query(Agent).filter(Agent.entity_id == agent_entity.id).first()
    config = (agent_row.config if agent_row else {}) or {}
    runtime = {
        **((agent_entity.metadata_ or {}).get("runtime") or {}),
        **(config.get("runtime") or {}),
    }
    runtime_type = runtime.get("type") or config.get("runtime_type")

    if agent_entity.name == "StudyAgent" or runtime_type == "study_agent":
        from services.study_agent import execute_study_agent

        return await execute_study_agent(
            db,
            human_entity_id=human_entity_id,
            topic=user_input,
            task_id=task_id,
            agent_entity_id=agent_entity.id,
            skill_entity_id=skill_entity_id,
            llm_entity_id=llm_entity_id,
            llm_provider=llm_provider,
            contribution_id=contribution_id,
            submit_contribution=submit_contribution,
        )

    if not skill_entity_id:
        caps = config.get("capabilities") or (agent_entity.metadata_ or {}).get("capabilities") or []
        if caps:
            skill_entity = (
                db.query(Entity)
                .filter(Entity.entity_type == EntityType.skill, Entity.name == caps[0])
                .first()
            )
            if skill_entity:
                skill_entity_id = skill_entity.id

    if not skill_entity_id:
        raise HTTPException(
            status_code=400,
            detail="Generic agent execution requires skill_entity_id or agent capabilities mapping to a Skill",
        )

    result = await execute_skill(
        db,
        human_entity_id=human_entity_id,
        skill_entity_id=skill_entity_id,
        user_input=user_input,
        context={**(context or {}), "agent": agent_entity.name, "agent_config": config},
        agent_entity_id=agent_entity.id,
        llm_entity_id=llm_entity_id,
        llm_provider=llm_provider,
        task_id=task_id,
        contribution_id=contribution_id,
    )
    result["execution_type"] = "agent"
    result["agent_entity_id"] = agent_entity.id
    result["agent_runtime"] = runtime_type or "generic_orchestrator"
    return result


def attach_receipt_to_result(db: Session, result: dict[str, Any]) -> dict[str, Any]:
    trace_id = result.get("trace_id")
    if not trace_id:
        return result
    trace = _load_trace(db, trace_id)
    result["receipt"] = build_agent_receipt(trace)
    return result
