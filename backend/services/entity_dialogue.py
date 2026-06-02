"""Entity Dialogue Protocol — native L2 envelope for Entity ↔ Entity communication.

Schema: pocp.entity_dialogue.v0.1
See docs/protocol/ENTITY-DIALOGUE-PROTOCOL.md
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

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
        "description": "Exchange intent before metered invoke (planned v0.2)",
        "connection_layer": "operational",
        "status": "planned",
    },
    "invoke": {
        "layer": "dialogue",
        "description": "Operational invoke along invocation edge matrix",
        "connection_layer": "operational",
    },
    "attest": {
        "layer": "dialogue",
        "description": "Witness or verify advisory on contribution or trace",
        "connection_layer": "protocol",
        "status": "partial",
    },
    "submit": {
        "layer": "dialogue",
        "description": "Open contribution event with participants",
        "connection_layer": "protocol",
        "status": "partial",
    },
    "finalize_notice": {
        "layer": "dialogue",
        "description": "Policy finalization notice",
        "connection_layer": "protocol",
        "status": "planned",
    },
    "federation_offer": {
        "layer": "dialogue",
        "description": "Offer signed contribution proof for peer import",
        "connection_layer": "protocol",
    },
    "federation_accept": {
        "layer": "dialogue",
        "description": "Accept or validate offered proof",
        "connection_layer": "protocol",
        "status": "planned",
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


def _handle_invoke(db: Session, envelope: dict[str, Any]) -> dict[str, Any]:
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
            "action": action,
            "step_order": step_order,
            "message": "Invocation step recorded; use bindings.execute for metered execution",
        },
        refs={
            "invocation_trace_id": trace.id,
            "invocation_step_id": step.id,
        },
        bindings=bindings,
    )


def _handle_federation_offer(db: Session, envelope: dict[str, Any]) -> dict[str, Any]:
    payload = envelope.get("payload") or {}
    proof = payload.get("proof")
    contribution_id = payload.get("contribution_id")
    source_node_id = (
        payload.get("source_node_id")
        or (envelope.get("from") or {}).get("node_id")
        or "unknown"
    )

    if proof and isinstance(proof, dict):
        validation = validate_proof_against_trust_policy(
            proof,
            source_node_id=source_node_id,
            raise_on_block=False,
        )
        return _response_envelope(
            envelope,
            status="accepted" if validation.get("blocking_valid") else "rejected",
            result={"validation": validation, "mode": "inline_proof"},
            errors=[] if validation.get("blocking_valid") else [c["id"] for c in validation.get("checks", []) if not c.get("ok")],
            bindings={
                "validate_proof": "/api/v1/federation/validate-proof",
                "import_proof": "/api/v1/federation/import-proof",
            },
        )

    if contribution_id:
        return _response_envelope(
            envelope,
            status="accepted",
            result={
                "mode": "proof_deref",
                "contribution_id": contribution_id,
                "source_node_id": source_node_id,
            },
            bindings={
                "proof": f"/api/v1/contributions/{contribution_id}/proof",
                "federation_export": f"/api/v1/intelligence/federation/export/{contribution_id}",
            },
        )

    return _response_envelope(
        envelope,
        status="rejected",
        errors=["payload.proof or payload.contribution_id required for federation_offer"],
    )


def _handle_attest(envelope: dict[str, Any]) -> dict[str, Any]:
    refs = envelope.get("refs") if isinstance(envelope.get("refs"), dict) else {}
    contribution_id = refs.get("contribution_id")
    if not contribution_id:
        return _response_envelope(
            envelope,
            status="rejected",
            errors=["refs.contribution_id required for attest"],
        )
    return _response_envelope(
        envelope,
        status="deferred",
        result={"message": "Attest routed to verification binding"},
        refs={"contribution_id": contribution_id},
        bindings={
            "auto_verify": f"/api/v1/contributions/{contribution_id}/auto-verify",
            "verdict": f"/api/v1/contributions/{contribution_id}/verdict",
        },
    )


def _handle_submit(envelope: dict[str, Any]) -> dict[str, Any]:
    return _response_envelope(
        envelope,
        status="deferred",
        result={"message": "Submit via dialogue binding until v0.2 full handler"},
        bindings={
            "submit_contribution": "/api/v1/contributions",
        },
    )


def route_dialogue(
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

    kind = envelope.get("kind")
    handlers = {
        "ping": lambda: _handle_ping(db, envelope),
        "discover": lambda: _handle_discover(db, envelope),
        "invoke": lambda: _handle_invoke(db, envelope),
        "federation_offer": lambda: _handle_federation_offer(db, envelope),
        "attest": lambda: _handle_attest(envelope),
        "submit": lambda: _handle_submit(envelope),
        "quote": lambda: _response_envelope(
            envelope,
            status="deferred",
            result={"message": "quote handler planned for v0.2"},
        ),
        "finalize_notice": lambda: _response_envelope(
            envelope,
            status="deferred",
            result={"message": "finalize_notice planned for v0.2"},
        ),
        "federation_accept": lambda: _response_envelope(
            envelope,
            status="deferred",
            result={"message": "federation_accept planned for v0.2"},
        ),
    }
    handler = handlers.get(kind)
    if not handler:
        return _response_envelope(envelope, status="rejected", errors=[f"unsupported kind: {kind}"])
    return handler()


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
            "overlay": "HTTPS on existing Internet",
            "node_model": "logical PoCP instance per BACKEND_URL",
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
        },
        "docs": "docs/protocol/ENTITY-DIALOGUE-PROTOCOL.md",
    }


def new_dialogue_id() -> str:
    return f"dlg_{uuid.uuid4().hex[:16]}"
