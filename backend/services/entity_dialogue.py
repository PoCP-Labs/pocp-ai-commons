"""Entity Dialogue Protocol — native L2 envelope for Entity ↔ Entity communication.

Schema: pocp.entity_dialogue.v0.1
See docs/protocol/ENTITY-DIALOGUE-PROTOCOL.md
"""

from __future__ import annotations

import inspect
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from intelligence.entity_ontology import invocation_action_for, validate_invocation_edge
from models.entity import Entity
from models.invocation import InvocationStatus, InvocationStep, InvocationTrace
from services.compute_registry import compute_status_manifest
from services.entity_connections import build_entity_connections
from services.entity_portable import find_entity_by_portable_id
from services.trust_policy_bundle import validate_proof_against_trust_policy

ENTITY_DIALOGUE_SCHEMA = "pocp.entity_dialogue.v0.1"
ENTITY_DIALOGUE_RESPONSE_SCHEMA = "pocp.entity_dialogue_response.v0.1"

DIALOGUE_KINDS: dict[str, dict[str, Any]] = {
    "ping": {
        "layer": None,
        "description": "Node or entity liveness probe",
        "connection_layer": None,
    },
    "discover": {
        "layer": "dialogue",
        "description": "Resolve entity profile, connections, and binding hints",
        "connection_layer": "structural",
    },
    "quote": {
        "layer": "dialogue",
        "description": "Exchange intent before metered invoke (cost estimate + exchange_id)",
        "connection_layer": "operational",
    },
    "invoke": {
        "layer": "dialogue",
        "description": "Operational invoke along invocation edge matrix",
        "connection_layer": "operational",
    },
    "attest": {
        "layer": "dialogue",
        "description": "Run auto-verify on contribution; returns consensus + verdict",
        "connection_layer": "protocol",
    },
    "submit": {
        "layer": "dialogue",
        "description": "Open contribution event with participants (optional auto_verify)",
        "connection_layer": "protocol",
    },
    "finalize_notice": {
        "layer": "dialogue",
        "description": "Policy finalization notice — verdict snapshot; optional apply_finalize",
        "connection_layer": "protocol",
    },
    "federation_offer": {
        "layer": "dialogue",
        "description": "Offer signed contribution proof for peer import",
        "connection_layer": "protocol",
    },
    "federation_accept": {
        "layer": "dialogue",
        "description": "Accept offered proof — validate, overlay enqueue, optional import",
        "connection_layer": "protocol",
    },
    "broadcast": {
        "layer": "dialogue",
        "description": "Publish ProtocolEvent to overlay mempool",
        "connection_layer": "protocol",
    },
}


def _node_id() -> str:
    return compute_status_manifest().get("node_id") or os.getenv("POCP_NODE_ID", "unknown")


def _entity_ref(entity: Entity) -> dict[str, Any]:
    meta = entity.metadata_ or {}
    ref: dict[str, Any] = {
        "entity_id": entity.id,
        "entity_type": entity.entity_type.value,
        "node_id": _node_id(),
    }
    portable = meta.get("portable_id")
    if portable:
        ref["portable_id"] = portable
    return ref


def _resolve_entity(db: Session, ref: dict[str, Any] | None) -> Entity | None:
    if not ref or not isinstance(ref, dict):
        return None
    entity_id = ref.get("entity_id")
    if entity_id:
        entity = db.query(Entity).filter(Entity.id == entity_id).first()
        if entity:
            return entity
    portable_id = ref.get("portable_id")
    if portable_id:
        return find_entity_by_portable_id(db, portable_id)
    return None


def validate_dialogue_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    """Structural validation — schema, kind, endpoints."""
    errors: list[str] = []
    if not isinstance(envelope, dict):
        return {"ok": False, "errors": ["envelope must be an object"]}

    schema = envelope.get("schema")
    if schema != ENTITY_DIALOGUE_SCHEMA:
        errors.append(f"schema must be {ENTITY_DIALOGUE_SCHEMA}")

    dialogue_id = envelope.get("dialogue_id")
    if not dialogue_id or not isinstance(dialogue_id, str):
        errors.append("dialogue_id is required")

    kind = envelope.get("kind")
    if kind not in DIALOGUE_KINDS:
        errors.append(f"kind must be one of: {', '.join(DIALOGUE_KINDS)}")

    for side in ("from", "to"):
        ref = envelope.get(side)
        if not isinstance(ref, dict):
            errors.append(f"{side} must be an object with entity_id and/or portable_id")
        elif not ref.get("entity_id") and not ref.get("portable_id"):
            errors.append(f"{side} requires entity_id or portable_id")

    payload = envelope.get("payload")
    if payload is not None and not isinstance(payload, dict):
        errors.append("payload must be an object when present")

    return {"ok": not errors, "errors": errors, "kind": kind}


def _response_envelope(
    request: dict[str, Any],
    *,
    status: str,
    result: dict[str, Any] | None = None,
    refs: dict[str, Any] | None = None,
    bindings: dict[str, Any] | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    from_ref = request.get("from") if isinstance(request.get("from"), dict) else {}
    to_ref = request.get("to") if isinstance(request.get("to"), dict) else {}
    return {
        "schema": ENTITY_DIALOGUE_RESPONSE_SCHEMA,
        "dialogue_id": request.get("dialogue_id"),
        "in_reply_to": request.get("dialogue_id"),
        "kind": request.get("kind"),
        "status": status,
        "from": {**to_ref, "node_id": to_ref.get("node_id") or _node_id()},
        "to": from_ref,
        "result": result or {},
        "refs": refs or {},
        "bindings": bindings or {},
        "errors": errors or [],
        "node_id": _node_id(),
        "responded_at": datetime.now(timezone.utc).isoformat(),
    }


def _handle_ping(_db: Session, envelope: dict[str, Any]) -> dict[str, Any]:
    return _response_envelope(
        envelope,
        status="accepted",
        result={
            "pong": True,
            "protocol": ENTITY_DIALOGUE_SCHEMA,
            "node_id": _node_id(),
        },
    )


def _handle_discover(db: Session, envelope: dict[str, Any]) -> dict[str, Any]:
    target = _resolve_entity(db, envelope.get("to"))
    if not target:
        return _response_envelope(
            envelope,
            status="rejected",
            errors=["target entity not found"],
        )

    connections = build_entity_connections(db, target.id)
    bindings = {
        "profile": f"/api/v1/intelligence/entities/{target.id}/profile",
        "connections": f"/api/v1/entities/{target.id}/connections",
        "agent_card": f"/api/v1/intelligence/entities/{target.id}/agent-card",
        "a2a": f"/api/v1/intelligence/entities/{target.id}/a2a",
        "dialogue": f"/api/v1/intelligence/entities/{target.id}/dialogue",
    }
    return _response_envelope(
        envelope,
        status="accepted",
        result={
            "entity": _entity_ref(target),
            "name": target.name,
            "description": target.description,
            "status": target.status.value,
            "connections": connections,
        },
        bindings=bindings,
    )


def _dialogue_user_input(payload: dict[str, Any]) -> str:
    raw = payload.get("input")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if isinstance(raw, dict):
        for key in ("topic", "prompt", "query", "text"):
            val = raw.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return str(raw)
    if isinstance(payload.get("prompt"), str):
        return payload["prompt"].strip()
    return "Execute via PoCP entity dialogue"


def _tag_trace_dialogue(db: Session, trace_id: str, envelope: dict[str, Any]) -> None:
    trace = (
        db.query(InvocationTrace)
        .options(joinedload(InvocationTrace.steps))
        .filter(InvocationTrace.id == trace_id)
        .first()
    )
    if not trace:
        return
    for step in trace.steps:
        meta = dict(step.metadata_ or {})
        meta["dialogue_id"] = envelope.get("dialogue_id")
        meta["dialogue_kind"] = "invoke"
        step.metadata_ = meta
    db.flush()


async def _handle_invoke_execute(
    db: Session,
    envelope: dict[str, Any],
    *,
    source: Entity,
    target: Entity,
    payload: dict[str, Any],
    refs_in: dict[str, Any],
) -> dict[str, Any]:
    from services.capability.dialogue_invoke import execute_metered_dialogue_invoke

    try:
        execution = await execute_metered_dialogue_invoke(
            db,
            source=source,
            target=target,
            payload=payload,
            refs_in=refs_in,
            dialogue_id=envelope.get("dialogue_id"),
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return _response_envelope(envelope, status="rejected", errors=[detail])

    trace_id = execution.get("trace_id")
    receipt = execution.get("receipt") if isinstance(execution.get("receipt"), dict) else None
    capability_receipts = execution.get("capability_receipts") or (
        receipt.get("capability_receipts") if receipt else []
    )

    return _response_envelope(
        envelope,
        status="accepted",
        result={
            "executed": True,
            "execution_type": execution.get("execution_type"),
            "output": execution.get("output"),
            "billing": execution.get("billing"),
            "mode": execution.get("mode"),
            "capability_receipts": capability_receipts,
            "receipt": receipt,
            "message": "Metered capability execution completed via dialogue invoke",
        },
        refs={
            "invocation_trace_id": trace_id,
            "capability_receipt_hashes": [
                r.get("receipt_hash") for r in capability_receipts if r.get("receipt_hash")
            ],
        },
        bindings={
            "invocation": f"/api/v1/invocations/{trace_id}" if trace_id else None,
            "receipt": f"/api/v1/integrations/invocations/{trace_id}/receipt" if trace_id else None,
        },
    )


def _handle_invoke_trace_only(
    db: Session,
    envelope: dict[str, Any],
    *,
    source: Entity,
    target: Entity,
    payload: dict[str, Any],
    action: str,
    refs_in: dict[str, Any],
) -> dict[str, Any]:
    trace_id = refs_in.get("invocation_trace_id")
    trace: InvocationTrace | None = None
    if trace_id:
        trace = db.query(InvocationTrace).filter(InvocationTrace.id == trace_id).first()

    if trace is None:
        trace = InvocationTrace(
            initiator_id=source.id,
            task_id=refs_in.get("task_id"),
            contribution_id=refs_in.get("contribution_id"),
            model_provider=payload.get("provider") or "dialogue",
            status=InvocationStatus.completed,
        )
        db.add(trace)
        db.flush()
        step_order = 1
    else:
        last = (
            db.query(InvocationStep)
            .filter(InvocationStep.trace_id == trace.id)
            .order_by(InvocationStep.step_order.desc())
            .first()
        )
        step_order = (last.step_order + 1) if last else 1

    step = InvocationStep(
        trace_id=trace.id,
        step_order=step_order,
        source_entity_id=source.id,
        target_entity_id=target.id,
        action=action,
        metadata_={
            "dialogue_id": envelope.get("dialogue_id"),
            "dialogue_kind": "invoke",
            "input": payload.get("input"),
            "exchange_id": refs_in.get("exchange_id") or payload.get("exchange_id"),
        },
    )
    db.add(step)
    db.flush()

    execute_binding: str | None = None
    if target.entity_type.value == "skill":
        execute_binding = f"/api/v1/capabilities/skills/{target.id}/execute"
    elif target.entity_type.value == "agent":
        execute_binding = f"/api/v1/capabilities/agents/{target.id}/execute"
    elif target.entity_type.value == "tool":
        execute_binding = f"/api/v1/capabilities/mcp/tools/{target.id}/invoke"

    bindings: dict[str, Any] = {
        "invocation": f"/api/v1/invocations/{trace.id}",
        "receipt": f"/api/v1/integrations/invocations/{trace.id}/receipt",
    }
    if execute_binding:
        bindings["execute"] = execute_binding

    return _response_envelope(
        envelope,
        status="accepted",
        result={
            "executed": False,
            "action": action,
            "step_order": step_order,
            "message": "Invocation step recorded; set payload.execute=true for metered execution",
        },
        refs={
            "invocation_trace_id": trace.id,
            "invocation_step_id": step.id,
        },
        bindings=bindings,
    )


def _handle_quote(db: Session, envelope: dict[str, Any]) -> dict[str, Any]:
    """PL-3: Pre-invoke exchange quote — wallet estimate + exchange_id for invoke chain."""
    from models.entity import EntityType
    from services.capability_execute import SKILL_EXECUTE_COST
    from services.exchange_spine import infer_exchange_kind, new_exchange_id
    from services.wallet_service import quote_spend

    source = _resolve_entity(db, envelope.get("from"))
    target = _resolve_entity(db, envelope.get("to"))
    if not source or not target:
        return _response_envelope(
            envelope,
            status="rejected",
            errors=["from and to entities must resolve on this node"],
        )

    if source.entity_type != EntityType.human:
        return _response_envelope(
            envelope,
            status="rejected",
            errors=["quote requires from entity to be human (billing anchor)"],
        )

    payload = envelope.get("payload") or {}
    action = payload.get("action") or invocation_action_for(
        source.entity_type.value,
        target.entity_type.value,
    )
    if not action:
        return _response_envelope(
            envelope,
            status="rejected",
            errors=["no invocation action for edge; provide payload.action"],
        )

    try:
        validate_invocation_edge(
            source.entity_type.value,
            target.entity_type.value,
            action,
            strict=True,
        )
    except ValueError as exc:
        return _response_envelope(envelope, status="rejected", errors=[str(exc)])

    quote_action = (payload.get("quote_action") or "").lower()
    if not quote_action:
        if target.entity_type in (EntityType.skill, EntityType.agent):
            quote_action = "capability_invoke"
        elif target.entity_type == EntityType.llm:
            quote_action = "ai_chat"
        else:
            quote_action = "capability_invoke"

    exchange_id = payload.get("exchange_id") or new_exchange_id()

    try:
        if quote_action == "ai_chat":
            quote = quote_spend(
                db,
                source.id,
                "ai_chat",
                cost=payload.get("cost"),
                provider=payload.get("llm_provider"),
            )
        elif quote_action == "capability_invoke":
            cost = float(payload.get("estimated_cost") or SKILL_EXECUTE_COST)
            from models.wallet import Wallet

            wallet = db.query(Wallet).filter(Wallet.entity_id == source.id).first()
            balance = float(wallet.ai_credits) if wallet else 0.0
            allowed = balance >= cost
            quote = {
                "action": "capability_invoke",
                "credit_type": "ai_credits",
                "cost": cost,
                "current_balance": round(balance, 6),
                "balance_after": round(balance - cost, 6) if allowed else round(balance, 6),
                "allowed": allowed,
                "target_entity_id": target.id,
                "target_entity_type": target.entity_type.value,
            }
        else:
            return _response_envelope(
                envelope,
                status="rejected",
                errors=[f"unsupported quote_action: {quote_action}"],
            )
    except ValueError as exc:
        return _response_envelope(envelope, status="rejected", errors=[str(exc)])

    skill_entity_id = target.id if target.entity_type == EntityType.skill else payload.get("skill_entity_id")
    exchange_kind = infer_exchange_kind(
        capability=payload.get("capability"),
        skill_entity_id=skill_entity_id,
        receipt=payload.get("receipt") if isinstance(payload.get("receipt"), dict) else None,
    )

    execute_binding: str | None = None
    if target.entity_type == EntityType.skill:
        execute_binding = f"/api/v1/capabilities/skills/{target.id}/execute"
    elif target.entity_type == EntityType.agent:
        execute_binding = f"/api/v1/capabilities/agents/{target.id}/execute"

    return _response_envelope(
        envelope,
        status="accepted",
        result={
            "mode": "exchange_quote",
            "exchange_id": exchange_id,
            "exchange_kind": exchange_kind,
            "quote": quote,
            "message": "Quote ready; follow with invoke (payload.execute=true) using refs.exchange_id",
        },
        refs={
            "exchange_id": exchange_id,
            "quoted_by_entity_id": source.id,
            "target_entity_id": target.id,
        },
        bindings={
            "invoke": f"/api/v1/intelligence/entities/{target.id}/dialogue",
            "execute": execute_binding,
            "wallet_quote": "/api/v1/wallets/me/quote",
        },
    )


async def _handle_invoke(db: Session, envelope: dict[str, Any]) -> dict[str, Any]:
    source = _resolve_entity(db, envelope.get("from"))
    target = _resolve_entity(db, envelope.get("to"))
    if not source or not target:
        return _response_envelope(
            envelope,
            status="rejected",
            errors=["from and to entities must resolve on this node"],
        )

    payload = envelope.get("payload") or {}
    action = payload.get("action") or invocation_action_for(
        source.entity_type.value,
        target.entity_type.value,
    )
    if not action:
        return _response_envelope(
            envelope,
            status="rejected",
            errors=[
                f"no invocation action for {source.entity_type.value} → {target.entity_type.value}; "
                "provide payload.action"
            ],
        )

    try:
        validate_invocation_edge(
            source.entity_type.value,
            target.entity_type.value,
            action,
            strict=True,
        )
    except ValueError as exc:
        return _response_envelope(envelope, status="rejected", errors=[str(exc)])

    refs_in = envelope.get("refs") if isinstance(envelope.get("refs"), dict) else {}
    if payload.get("execute"):
        return await _handle_invoke_execute(
            db, envelope, source=source, target=target, payload=payload, refs_in=refs_in
        )
    return _handle_invoke_trace_only(
        db, envelope, source=source, target=target, payload=payload, action=action, refs_in=refs_in
    )


def _handle_federation_offer(db: Session, envelope: dict[str, Any]) -> dict[str, Any]:
    from services.network.federation_overlay import relay_federation_offer

    payload = envelope.get("payload") or {}
    proof = payload.get("proof") if isinstance(payload.get("proof"), dict) else None
    contribution_id = payload.get("contribution_id")
    source_node_id = (
        payload.get("source_node_id")
        or (envelope.get("from") or {}).get("node_id")
        or "unknown"
    )
    fetch_peer = payload.get("fetch_peer", True)
    auto_import = bool(payload.get("auto_import", False))

    if proof or (contribution_id and fetch_peer):
        try:
            relay = relay_federation_offer(
                db,
                source_node_id=source_node_id,
                contribution_id=contribution_id,
                proof=proof,
                auto_import=auto_import,
                dialogue_id=envelope.get("dialogue_id"),
            )
        except ValueError as exc:
            return _response_envelope(envelope, status="rejected", errors=[str(exc)])

        validation = relay["validation"]
        ok = bool(validation.get("blocking_valid"))
        return _response_envelope(
            envelope,
            status="accepted" if ok else "rejected",
            result=relay,
            refs={
                "protocol_event_id": relay["overlay_event"]["event_id"],
                "contribution_id": relay.get("contribution_id"),
            },
            errors=[] if ok else [c["id"] for c in validation.get("checks", []) if not c.get("ok")],
            bindings={
                "validate_proof": "/api/v1/federation/validate-proof",
                "import_proof": "/api/v1/federation/import-proof",
                "overlay_relay": "/api/v1/federation/overlay/relay",
            },
        )

    if contribution_id:
        peer_url = None
        try:
            from services.network.federation_overlay import resolve_trusted_peer

            peer_url = resolve_trusted_peer(source_node_id)["base_url"]
        except ValueError:
            pass
        return _response_envelope(
            envelope,
            status="accepted",
            result={
                "mode": "proof_deref",
                "contribution_id": contribution_id,
                "source_node_id": source_node_id,
                "fetch_peer": False,
            },
            bindings={
                "proof": f"{peer_url}/api/v1/contributions/{contribution_id}/proof" if peer_url else None,
                "federation_export": (
                    f"{peer_url}/api/v1/intelligence/federation/export/{contribution_id}"
                    if peer_url
                    else None
                ),
            },
        )

    return _response_envelope(
        envelope,
        status="rejected",
        errors=["payload.proof or payload.contribution_id required for federation_offer"],
    )


def _handle_federation_accept(db: Session, envelope: dict[str, Any]) -> dict[str, Any]:
    from services.network.federation_overlay import federation_accept_from_proof

    payload = envelope.get("payload") or {}
    proof = payload.get("proof") if isinstance(payload.get("proof"), dict) else None
    source_node_id = (
        payload.get("source_node_id")
        or (envelope.get("from") or {}).get("node_id")
        or "unknown"
    )
    auto_import = bool(payload.get("auto_import", True))

    if not proof and payload.get("contribution_id"):
        try:
            from services.network.federation_overlay import fetch_proof_from_peer

            proof = fetch_proof_from_peer(source_node_id, payload["contribution_id"])
        except ValueError as exc:
            return _response_envelope(envelope, status="rejected", errors=[str(exc)])

    if not proof:
        return _response_envelope(
            envelope,
            status="rejected",
            errors=["payload.proof or fetchable contribution_id required for federation_accept"],
        )

    try:
        relay = federation_accept_from_proof(
            db,
            source_node_id=source_node_id,
            proof=proof,
            auto_import=auto_import,
            dialogue_id=envelope.get("dialogue_id"),
        )
    except ValueError as exc:
        return _response_envelope(envelope, status="rejected", errors=[str(exc)])

    validation = relay["validation"]
    ok = bool(validation.get("blocking_valid"))
    imported = (relay.get("import") or {}).get("imported")
    status = "accepted" if ok and (not auto_import or imported) else "rejected"
    if ok and auto_import and not imported:
        status = "rejected"

    return _response_envelope(
        envelope,
        status=status,
        result=relay,
        refs={
            "protocol_event_id": relay["overlay_event"]["event_id"],
            "contribution_id": relay.get("contribution_id"),
            "federated_import_id": (relay.get("import") or {}).get("federated_import_id"),
        },
        errors=[] if status == "accepted" else ["federation_accept failed validation or import"],
        bindings={
            "overlay_relay": "/api/v1/federation/overlay/relay",
            "import_proof": "/api/v1/federation/import-proof",
        },
    )


def _handle_finalize_notice(db: Session, envelope: dict[str, Any]) -> dict[str, Any]:
    """Policy finalization notice — inspect verdict; optional apply via auto-policy or finalizer entity."""
    from models.contribution import ContributionEvent, ContributionStatus
    from services.contribution import approve_contribution
    from services.finalization import (
        build_verdict_snapshot,
        consensus_from_contribution,
        finalization_policy_manifest,
        try_auto_finalize_after_verify,
        validate_finalizer_entity,
    )

    refs = envelope.get("refs") if isinstance(envelope.get("refs"), dict) else {}
    payload = envelope.get("payload") if isinstance(envelope.get("payload"), dict) else {}
    contribution_id = refs.get("contribution_id") or payload.get("contribution_id")
    if not contribution_id:
        return _response_envelope(
            envelope,
            status="rejected",
            errors=["refs.contribution_id or payload.contribution_id required for finalize_notice"],
        )

    contribution = (
        db.query(ContributionEvent)
        .filter(ContributionEvent.id == contribution_id)
        .first()
    )
    if not contribution:
        return _response_envelope(
            envelope,
            status="rejected",
            errors=[f"contribution not found: {contribution_id}"],
        )

    policy_manifest = finalization_policy_manifest()
    verdict = build_verdict_snapshot(contribution)
    finalizer = _resolve_entity(db, envelope.get("from"))

    result: dict[str, Any] = {
        "mode": "finalize_notice",
        "contribution_id": contribution_id,
        "contribution_status": contribution.status.value,
        "verdict": verdict,
        "policy": {
            "policy_id": policy_manifest.get("policy_id"),
            "auto_finalization_enabled": policy_manifest.get("auto_finalization_enabled"),
            "default_finalizer_entity_id": policy_manifest.get("default_finalizer_entity_id"),
        },
        "can_finalize": contribution.status == ContributionStatus.ai_verified,
    }

    applied: dict[str, Any] | None = None
    if payload.get("apply_finalize") and contribution.status == ContributionStatus.ai_verified:
        consensus = consensus_from_contribution(contribution)
        if payload.get("use_auto_policy", True) and consensus:
            auto = try_auto_finalize_after_verify(db, contribution, consensus)
            if auto and auto.get("applied"):
                applied = auto
                result["contribution_status"] = contribution.status.value
            elif auto:
                applied = {"applied": False, "reason": auto.get("reason") or "policy_not_eligible", **auto}
            else:
                applied = {"applied": False, "reason": "auto_finalize_skipped"}
        elif finalizer:
            try:
                validate_finalizer_entity(finalizer)
                rewards = approve_contribution(
                    db,
                    contribution,
                    finalizer.id,
                    payload.get("feedback") or "Approved via finalize_notice dialogue.",
                    finalization={
                        "mode": "dialogue_finalize_notice",
                        "dialogue_id": envelope.get("dialogue_id"),
                        "finalizer_entity_id": finalizer.id,
                    },
                )
                applied = {
                    "applied": True,
                    "mode": "manual_finalizer",
                    "finalizer_entity_id": finalizer.id,
                    "rewards": rewards,
                }
                result["contribution_status"] = contribution.status.value
            except ValueError as exc:
                return _response_envelope(envelope, status="rejected", errors=[str(exc)])
        else:
            return _response_envelope(
                envelope,
                status="rejected",
                errors=["apply_finalize requires consensus (use_auto_policy) or resolvable from entity"],
            )
    elif payload.get("apply_finalize"):
        return _response_envelope(
            envelope,
            status="rejected",
            errors=[f"contribution status {contribution.status.value} cannot be finalized"],
        )

    if applied is not None:
        result["finalization"] = applied

    bindings = {
        "finalize": f"/api/v1/contributions/{contribution_id}/finalize",
        "verdict": f"/api/v1/contributions/{contribution_id}/verdict",
        "proof": f"/api/v1/contributions/{contribution_id}/proof",
        "finalization_policy": "/api/v1/intelligence/finalization-policy",
    }

    return _response_envelope(
        envelope,
        status="accepted",
        result=result,
        refs={"contribution_id": contribution_id},
        bindings=bindings,
    )


def _dialogue_http_error(envelope: dict[str, Any], exc: HTTPException) -> dict[str, Any]:
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return _response_envelope(envelope, status="rejected", errors=[detail])


async def _handle_attest(db: Session, envelope: dict[str, Any]) -> dict[str, Any]:
    """Witness / verify contribution — runs capability_layer.verify_contribution when run_verify."""
    from fastapi import HTTPException

    from intelligence import capability_layer
    from models.contribution import ContributionEvent, ContributionStatus
    from models.entity import EntityType
    from services.finalization import build_verdict_snapshot

    refs = envelope.get("refs") if isinstance(envelope.get("refs"), dict) else {}
    payload = envelope.get("payload") if isinstance(envelope.get("payload"), dict) else {}
    contribution_id = refs.get("contribution_id") or payload.get("contribution_id")
    if not contribution_id:
        return _response_envelope(
            envelope,
            status="rejected",
            errors=["refs.contribution_id or payload.contribution_id required for attest"],
        )

    attester = _resolve_entity(db, envelope.get("from"))
    if not attester:
        return _response_envelope(envelope, status="rejected", errors=["from entity must resolve on this node"])

    contribution = (
        db.query(ContributionEvent)
        .filter(ContributionEvent.id == contribution_id)
        .first()
    )
    if not contribution:
        return _response_envelope(
            envelope,
            status="rejected",
            errors=[f"contribution not found: {contribution_id}"],
        )

    run_verify = payload.get("run_verify", True)
    if run_verify:
        if attester.entity_type != EntityType.human:
            return _response_envelope(
                envelope,
                status="rejected",
                errors=["run_verify requires from entity to be human (contribution owner anchor)"],
            )
        if contribution.primary_entity_id != attester.id:
            return _response_envelope(
                envelope,
                status="rejected",
                errors=["only contribution primary_entity may run attest verify on this node"],
            )
        if contribution.status not in (ContributionStatus.submitted, ContributionStatus.draft):
            return _response_envelope(
                envelope,
                status="rejected",
                errors=[f"cannot verify contribution in status: {contribution.status.value}"],
            )
        try:
            consensus = await capability_layer.verify_contribution(db, contribution)
        except HTTPException as exc:
            return _dialogue_http_error(envelope, exc)
        verdict = build_verdict_snapshot(contribution)
        return _response_envelope(
            envelope,
            status="accepted",
            result={
                "mode": "attest_verify",
                "contribution_id": contribution_id,
                "contribution_status": contribution.status.value,
                "consensus": consensus,
                "verdict": verdict,
                "finalization": consensus.get("finalization"),
            },
            refs={"contribution_id": contribution_id},
            bindings={
                "verdict": f"/api/v1/contributions/{contribution_id}/verdict",
                "proof": f"/api/v1/contributions/{contribution_id}/proof",
                "finalize_notice": "/api/v1/intelligence/dialogue",
            },
        )

    verdict = build_verdict_snapshot(contribution)
    return _response_envelope(
        envelope,
        status="accepted",
        result={
            "mode": "attest_inspect",
            "contribution_id": contribution_id,
            "contribution_status": contribution.status.value,
            "verdict": verdict,
            "message": "Inspection only; set payload.run_verify=true to execute auto-verify",
        },
        refs={"contribution_id": contribution_id},
        bindings={
            "auto_verify": f"/api/v1/contributions/{contribution_id}/auto-verify",
            "verdict": f"/api/v1/contributions/{contribution_id}/verdict",
        },
    )


async def _handle_submit(db: Session, envelope: dict[str, Any]) -> dict[str, Any]:
    """Submit contribution via native dialogue envelope."""
    from fastapi import HTTPException

    from intelligence import capability_layer
    from models.entity import EntityType
    from services.contribution_submit import submit_contribution_event

    source = _resolve_entity(db, envelope.get("from"))
    if not source:
        return _response_envelope(envelope, status="rejected", errors=["from entity must resolve on this node"])
    if source.entity_type != EntityType.human:
        return _response_envelope(
            envelope,
            status="rejected",
            errors=["submit requires from entity to be human (primary_entity)"],
        )

    payload = envelope.get("payload") if isinstance(envelope.get("payload"), dict) else {}
    task_id = payload.get("task_id")
    if not task_id:
        return _response_envelope(envelope, status="rejected", errors=["payload.task_id required for submit"])

    try:
        contribution = submit_contribution_event(
            db,
            human_entity_id=source.id,
            task_id=task_id,
            contribution_type=payload.get("contribution_type") or "knowledge",
            description=payload.get("description"),
            evidence=payload.get("evidence") if isinstance(payload.get("evidence"), dict) else {},
            participants=payload.get("participants") if isinstance(payload.get("participants"), list) else [],
            provenance=payload.get("provenance") if isinstance(payload.get("provenance"), dict) else None,
        )
    except HTTPException as exc:
        return _dialogue_http_error(envelope, exc)

    meta = dict((contribution.evidence or {}).get("_pocp") or {})
    meta["dialogue_id"] = envelope.get("dialogue_id")
    meta["dialogue_kind"] = "submit"
    evidence = dict(contribution.evidence or {})
    evidence["_pocp"] = meta
    contribution.evidence = evidence
    db.flush()

    verification: dict[str, Any] | None = None
    if payload.get("auto_verify"):
        try:
            verification = await capability_layer.verify_contribution(db, contribution)
        except HTTPException as exc:
            return _dialogue_http_error(envelope, exc)

    result: dict[str, Any] = {
        "mode": "submit",
        "contribution_id": contribution.id,
        "contribution_status": contribution.status.value,
        "task_id": task_id,
        "participant_count": len(contribution.participants or []),
    }
    if verification is not None:
        result["verification"] = verification
        result["contribution_status"] = contribution.status.value
        result["finalization"] = verification.get("finalization")

    return _response_envelope(
        envelope,
        status="accepted",
        result=result,
        refs={
            "contribution_id": contribution.id,
            "task_id": task_id,
        },
        bindings={
            "attest": "/api/v1/intelligence/dialogue",
            "auto_verify": f"/api/v1/contributions/{contribution.id}/auto-verify",
            "proof": f"/api/v1/contributions/{contribution.id}/proof",
            "finalize_notice": "/api/v1/intelligence/dialogue",
        },
    )


def _handle_broadcast(envelope: dict[str, Any]) -> dict[str, Any]:
    from services.network.protocol_bridge import protocol_event_from_dialogue, protocol_event_to_dict
    from services.network.runtime import enqueue_event

    event = protocol_event_from_dialogue(envelope)
    if event is None:
        return _response_envelope(
            envelope,
            status="rejected",
            errors=["broadcast requires payload.event_type or valid dialogue kind"],
        )
    doc = enqueue_event(event)
    return _response_envelope(
        envelope,
        status="accepted",
        result={"message": "ProtocolEvent enqueued to overlay mempool", "event": doc},
        refs={"protocol_event_id": doc["event_id"]},
        bindings={"overlay_status": "/api/v1/intelligence/network/overlay/status"},
    )


def _attach_overlay(response: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    """Emit ProtocolEvent to overlay when dialogue kind maps to network layer."""
    if response.get("status") not in ("accepted", "deferred"):
        return response
    result_body = response.get("result") if isinstance(response.get("result"), dict) else {}
    pre_enqueued = result_body.get("overlay_event")
    if isinstance(pre_enqueued, dict) and pre_enqueued.get("event_id"):
        refs = dict(response.get("refs") or {})
        refs.setdefault("protocol_event_id", pre_enqueued["event_id"])
        overlay = dict(response.get("overlay") or {})
        overlay["protocol_event"] = pre_enqueued
        return {**response, "refs": refs, "overlay": overlay}
    from services.network.protocol_bridge import (
        DIALOGUE_KINDS_EMITTING_OVERLAY,
        protocol_event_from_dialogue,
        protocol_event_to_dict,
    )
    from services.network.runtime import enqueue_event

    kind = envelope.get("kind")
    if kind not in DIALOGUE_KINDS_EMITTING_OVERLAY or kind == "broadcast":
        return response
    event = protocol_event_from_dialogue(envelope)
    if event is None:
        return response
    doc = enqueue_event(event)
    refs = dict(response.get("refs") or {})
    refs["protocol_event_id"] = doc["event_id"]
    response = {**response, "refs": refs}
    overlay = response.get("overlay") or {}
    overlay["protocol_event"] = protocol_event_to_dict(event)
    response["overlay"] = overlay
    return response


async def route_dialogue(
    db: Session,
    envelope: dict[str, Any],
    *,
    expected_target_entity_id: str | None = None,
) -> dict[str, Any]:
    """Validate and dispatch a dialogue envelope on this node."""
    validation = validate_dialogue_envelope(envelope)
    if not validation["ok"]:
        return _response_envelope(
            envelope if isinstance(envelope, dict) else {},
            status="rejected",
            errors=validation["errors"],
        )

    if expected_target_entity_id:
        to_ref = envelope.get("to") if isinstance(envelope.get("to"), dict) else {}
        to_id = to_ref.get("entity_id")
        if to_id and to_id != expected_target_entity_id:
            return _response_envelope(
                envelope,
                status="rejected",
                errors=[f"to.entity_id must match path entity {expected_target_entity_id}"],
            )
        if not to_id:
            to_ref = {**to_ref, "entity_id": expected_target_entity_id}
            envelope = {**envelope, "to": to_ref}

    from services.network.dialogue_route import try_peer_route_dialogue

    peer_response = try_peer_route_dialogue(db, envelope, resolve_target=_resolve_entity)
    if peer_response is not None:
        return peer_response

    kind = envelope.get("kind")
    handlers = {
        "ping": lambda: _handle_ping(db, envelope),
        "discover": lambda: _handle_discover(db, envelope),
        "invoke": lambda: _handle_invoke(db, envelope),
        "federation_offer": lambda: _handle_federation_offer(db, envelope),
        "attest": lambda: _handle_attest(db, envelope),
        "submit": lambda: _handle_submit(db, envelope),
        "quote": lambda: _handle_quote(db, envelope),
        "finalize_notice": lambda: _handle_finalize_notice(db, envelope),
        "federation_accept": lambda: _handle_federation_accept(db, envelope),
        "broadcast": lambda: _handle_broadcast(envelope),
    }
    handler = handlers.get(kind)
    if not handler:
        return _response_envelope(envelope, status="rejected", errors=[f"unsupported kind: {kind}"])
    result = handler()
    if inspect.isawaitable(result):
        result = await result
    return _attach_overlay(result, envelope)


def dialogue_manifest() -> dict[str, Any]:
    """Protocol descriptor for GET /protocol/entity-dialogue."""
    return {
        "schema": ENTITY_DIALOGUE_SCHEMA,
        "response_schema": ENTITY_DIALOGUE_RESPONSE_SCHEMA,
        "spec_version": "0.1",
        "stack_layer": "L2_dialogue",
        "stack_layer_zh": "对话层",
        "principle": "One native envelope for all Entity dialogue; bindings are adapters.",
        "principle_zh": "Entity 对话统一走 PoCP 信封；REST/A2A/MCP 是绑定层。",
        "transport": {
            "physical_network": "none",
            "overlay": "HTTPS on existing Internet (public URL per node)",
            "node_model": "logical PoCP instance per BACKEND_URL",
            "peer_route_env": "POCP_DIALOGUE_PEER_ROUTE",
            "trusted_peers_env": "POCP_TRUSTED_NODES",
            "peer_dialogue_api": "/api/v1/federation/dialogue",
        },
        "kinds": DIALOGUE_KINDS,
        "endpoints": {
            "dialogue": "/api/v1/intelligence/dialogue",
            "entity_dialogue": "/api/v1/intelligence/entities/{entity_id}/dialogue",
            "manifest": "/api/v1/intelligence/protocol/entity-dialogue",
        },
        "related": {
            "entity_connection": "pocp.entity_connection.v0.1",
            "capability_receipt": "pocp.capability_receipt.v0.1",
            "trust_policy_bundle": "pocp.trust_policy_bundle.v0.1",
            "protocol_event_network": "pocp.protocol_event.v0.1",
        },
        "docs": "docs/protocol/ENTITY-DIALOGUE-PROTOCOL.md",
        "overlay_docs": "docs/protocol/PROTOCOL-EVENT-NETWORK.md",
        "binding_map": "docs/protocol/BINDING-TO-DIALOGUE.md",
    }


def new_dialogue_id() -> str:
    return f"dlg_{uuid.uuid4().hex[:16]}"
