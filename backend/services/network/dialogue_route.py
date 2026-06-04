"""Cross-node Entity Dialogue routing over public Internet (HTTPS overlay)."""

from __future__ import annotations

import logging
import os
from typing import Any

from services.compute_registry import compute_status_manifest
from services.federation_peers import _post_json
from services.trust_config import trusted_nodes_map

logger = logging.getLogger(__name__)

ROUTABLE_KINDS = frozenset(
    {
        "ping",
        "discover",
        "quote",
        "invoke",
        "broadcast",
        "federation_offer",
        "federation_accept",
    }
)
FEDERATION_DIALOGUE_PATH = "/api/v1/federation/dialogue"


def peer_route_enabled() -> bool:
    return os.getenv("POCP_DIALOGUE_PEER_ROUTE", "true").lower() in ("true", "1", "yes", "on")


def local_node_id() -> str:
    return compute_status_manifest().get("node_id") or os.getenv("POCP_NODE_ID", "unknown")


def resolve_trusted_peer(node_id: str) -> dict[str, Any] | None:
    peer = trusted_nodes_map().get(node_id)
    if peer is None:
        return None
    return {
        "node_id": peer.node_id,
        "base_url": peer.base_url.rstrip("/"),
        "trust_weight": float(peer.trust_weight),
    }


def resolve_runtime_peer(db, node_id: str) -> dict[str, Any] | None:
    """
    Resolve peer from trusted config first, then discovered DB entities.
    This enables immediate connectivity after UI "register peer".
    """
    peer = resolve_trusted_peer(node_id)
    if peer is not None:
        return peer
    if db is None:
        return None
    try:
        from models.entity import Entity
        from services.federation_community import peer_entity_id

        entity = db.get(Entity, peer_entity_id(node_id))
        if not entity:
            return None
        meta = entity.metadata_ or {}
        from services.federation_peer_addrbook import is_peer_routable

        if not is_peer_routable(meta):
            return None
        roles = meta.get("roles") or []
        if "federation_peer" not in roles and "discovered_peer" not in roles:
            return None
        base_url = (meta.get("probe_base_url") or meta.get("base_url") or "").rstrip("/")
        public_url = (meta.get("public_base_url") or meta.get("base_url") or base_url).rstrip("/")
        if not base_url:
            return None
        return {
            "node_id": node_id,
            "base_url": base_url,
            "public_base_url": public_url,
            "trust_weight": float(meta.get("trust_weight") or 0.5),
            "discovered": True,
        }
    except Exception:
        return None


def should_route_to_peer(
    envelope: dict[str, Any],
    *,
    target_resolved_locally: bool,
) -> tuple[bool, str | None]:
    """
    Decide if envelope should be forwarded to to.node_id peer.
    Returns (route, peer_node_id).
    """
    if not peer_route_enabled():
        return False, None

    to_ref = envelope.get("to") if isinstance(envelope.get("to"), dict) else {}
    peer_node = to_ref.get("node_id")
    if not peer_node or peer_node == local_node_id():
        return False, None

    kind = envelope.get("kind")
    if kind not in ROUTABLE_KINDS:
        return False, None

    payload = envelope.get("payload") if isinstance(envelope.get("payload"), dict) else {}
    if payload.get("route_peer") is True:
        return True, peer_node
    if payload.get("route_peer") is False:
        return False, None

    # Auto-route when target is not on this node (portable_id or unknown entity_id)
    if not target_resolved_locally:
        return True, peer_node

    return False, None


def forward_dialogue_to_peer(peer_base_url: str, envelope: dict[str, Any]) -> dict[str, Any]:
    """POST envelope to peer's federation dialogue surface (no end-user JWT required)."""
    url = f"{peer_base_url.rstrip('/')}{FEDERATION_DIALOGUE_PATH}"
    outbound = {**envelope}
    from_ref = dict(outbound.get("from") or {})
    from_ref.setdefault("node_id", local_node_id())
    outbound["from"] = from_ref
    refs = dict(outbound.get("refs") or {})
    refs["routed_from_node_id"] = local_node_id()
    outbound["refs"] = refs

    remote = _post_json(url, outbound, timeout=float(os.getenv("POCP_PEER_DIALOGUE_TIMEOUT", "120")))
    if not isinstance(remote, dict):
        raise ValueError("Peer returned non-object dialogue response")
    return remote


def wrap_peer_route_response(
    request: dict[str, Any],
    remote: dict[str, Any],
    *,
    peer: dict[str, Any],
    local_trace_id: str | None = None,
) -> dict[str, Any]:
    """Attach peer routing metadata to the remote dialogue response."""
    result = dict(remote.get("result") or {})
    result["peer_route"] = True
    result["routed_via"] = {
        "peer_node_id": peer["node_id"],
        "peer_base_url": peer.get("public_base_url") or peer["base_url"],
        "local_node_id": local_node_id(),
    }
    remote = {**remote, "result": result}
    refs = dict(remote.get("refs") or {})
    if local_trace_id:
        refs["invocation_trace_id"] = local_trace_id
        peer_trace = (remote.get("refs") or {}).get("invocation_trace_id")
        if peer_trace and peer_trace != local_trace_id:
            refs["peer_invocation_trace_id"] = peer_trace
    remote["refs"] = refs
    bindings = dict(remote.get("bindings") or {})
    bindings["peer_dialogue"] = f"{peer['base_url']}{FEDERATION_DIALOGUE_PATH}"
    if local_trace_id:
        bindings["invocation"] = f"/api/v1/invocations/{local_trace_id}"
    remote["bindings"] = bindings
    return remote


def _peer_route_settlement_key(envelope: dict[str, Any], peer_node_id: str) -> str:
    dialogue_id = str(envelope.get("dialogue_id") or "")
    kind = str(envelope.get("kind") or "")
    return f"peer_route:{peer_node_id}:{kind}:{dialogue_id}"


def record_peer_route_exchange_on_originator(
    db,
    envelope: dict[str, Any],
    remote: dict[str, Any],
    *,
    peer: dict[str, Any],
    local_trace_id: str | None = None,
    local_target_entity_id: str | None = None,
) -> str | None:
    """
    Originating-node exchange_settled for cross-node quote→invoke chains.

    Execution and primary billing may occur on the peer; this row anchors the
    consumer exchange trail on the originator (CIP-P2.1).
    """
    kind = envelope.get("kind")
    if kind not in ("quote", "invoke"):
        return None
    if remote.get("status") != "accepted" or db is None:
        return None

    from_ref = envelope.get("from") if isinstance(envelope.get("from"), dict) else {}
    consumer_id = from_ref.get("entity_id")
    if not consumer_id and from_ref.get("portable_id"):
        try:
            from services.entity_portable import find_entity_by_portable_id

            resolved = find_entity_by_portable_id(db, str(from_ref.get("portable_id")))
            if resolved is not None:
                consumer_id = resolved.id
        except Exception:
            pass
    if not consumer_id:
        return None

    try:
        from models.entity import Entity, EntityType
        from models.ledger import LedgerRecord

        consumer = db.get(Entity, consumer_id)
        if consumer is None or consumer.entity_type != EntityType.human:
            return None

        settlement_key = _peer_route_settlement_key(envelope, peer["node_id"])
        recent = (
            db.query(LedgerRecord)
            .filter(LedgerRecord.event_type == "exchange_settled")
            .order_by(LedgerRecord.created_at.desc())
            .limit(80)
            .all()
        )
        for row in recent:
            pl = row.payload if isinstance(row.payload, dict) else {}
            if pl.get("peer_route_settlement_key") == settlement_key:
                return pl.get("exchange_id")

        remote_refs = remote.get("refs") if isinstance(remote.get("refs"), dict) else {}
        remote_result = remote.get("result") if isinstance(remote.get("result"), dict) else {}
        refs_in = envelope.get("refs") if isinstance(envelope.get("refs"), dict) else {}
        payload_in = envelope.get("payload") if isinstance(envelope.get("payload"), dict) else {}

        exchange_id = (
            remote_refs.get("exchange_id")
            or remote_result.get("exchange_id")
            or refs_in.get("exchange_id")
            or payload_in.get("exchange_id")
        )
        billing = remote_result.get("billing") if isinstance(remote_result.get("billing"), dict) else {}
        peer_exchange_id = billing.get("exchange_id") or remote_refs.get("peer_exchange_id")

        provider_id = local_target_entity_id
        if provider_id and db.get(Entity, provider_id) is None:
            provider_id = None
        if not provider_id:
            from services.federation_community import peer_entity_id

            fallback = peer_entity_id(peer["node_id"])
            if db.get(Entity, fallback) is not None:
                provider_id = fallback
        if not provider_id:
            provider_id = consumer_id

        from services.capability_execute import SKILL_EXECUTE_COST
        from services.exchange_spine import emit_zero_cost_exchange, infer_exchange_kind

        capability = payload_in.get("capability") or "skill_invocation"
        exchange_kind = infer_exchange_kind(
            capability=capability,
            skill_entity_id=payload_in.get("skill_entity_id"),
        )
        peer_trace = remote_refs.get("invocation_trace_id") or remote_refs.get("peer_invocation_trace_id")
        receipt_hash = None
        if isinstance(remote_result.get("receipt"), dict):
            receipt_hash = (remote_result["receipt"].get("integrity") or {}).get("receipt_hash")

        extra = {
            "peer_route": True,
            "peer_route_settlement_key": settlement_key,
            "peer_node_id": peer["node_id"],
            "peer_base_url": peer.get("public_base_url") or peer["base_url"],
            "dialogue_kind": kind,
            "dialogue_id": envelope.get("dialogue_id"),
            "peer_exchange_id": peer_exchange_id,
            "peer_invocation_trace_id": peer_trace,
            "routed_from_node_id": local_node_id(),
        }

        if kind == "quote":
            if not exchange_id:
                from services.exchange_spine import new_exchange_id

                exchange_id = new_exchange_id()
            record = emit_zero_cost_exchange(
                db,
                consumer_entity_id=consumer_id,
                provider_entity_ids=[provider_id],
                capability=capability,
                receipt_hash=receipt_hash,
                invocation_trace_id=local_trace_id,
                settlement_policy="peer_route.quote.v1",
                extra_payload={**extra, "exchange_id": exchange_id, "exchange_kind": exchange_kind},
            )
            db.commit()
            return (record.payload or {}).get("exchange_id") or exchange_id

        # invoke — originator debit when peer returned billing or quote chain refs
        execute = payload_in.get("execute") is True
        cost = float(billing.get("credits_spent") or 0.0)
        if cost <= 0 and execute:
            cost = float(payload_in.get("estimated_cost") or SKILL_EXECUTE_COST)

        if cost <= 0:
            if not exchange_id:
                from services.exchange_spine import new_exchange_id

                exchange_id = new_exchange_id()
            record = emit_zero_cost_exchange(
                db,
                consumer_entity_id=consumer_id,
                provider_entity_ids=[provider_id],
                capability=capability,
                receipt_hash=receipt_hash,
                invocation_trace_id=local_trace_id,
                settlement_policy="peer_route.invoke_trace.v1",
                extra_payload={**extra, "exchange_id": exchange_id, "exchange_kind": exchange_kind},
            )
            db.commit()
            return (record.payload or {}).get("exchange_id") or exchange_id

        from services.exchange_spine import settle_flat_metered_invoke

        settled = settle_flat_metered_invoke(
            db,
            entity_id=consumer_id,
            prompt=str(payload_in.get("input") or "")[:4000],
            response=str(remote_result.get("output") or remote_result.get("message") or "")[:4000],
            provider=str(billing.get("provider") or "peer_route"),
            model=str(billing.get("model") or peer["node_id"]),
            cost=cost,
            reason=f"peer_route_invoke:{peer['node_id']}",
            provider_entity_id=provider_id,
            capability=capability,
            receipt_hash=receipt_hash,
            invocation_trace_id=local_trace_id,
            settlement_policy="peer_route.invoke.v1",
        )
        exchange_id = settled.get("exchange_id") or exchange_id
        if exchange_id:
            from services.entity_local_chain import find_exchange_ledger_record

            record = find_exchange_ledger_record(db, exchange_id)
            if record and isinstance(record.payload, dict):
                record.payload = {**record.payload, **extra, "exchange_id": exchange_id}
                db.add(record)
        db.commit()
        return exchange_id
    except Exception as exc:
        logger.debug("peer route originator exchange skipped: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
        return None


def record_peer_route_trace_stub(
    db,
    envelope: dict[str, Any],
    remote: dict[str, Any],
    *,
    peer: dict[str, Any],
    local_target_entity_id: str | None = None,
) -> str | None:
    """Originating-node invocation trace for cross-node invoke/quote (audit stub)."""
    if envelope.get("kind") not in ("invoke", "quote"):
        return None
    if remote.get("status") != "accepted" or db is None:
        return None

    from_ref = envelope.get("from") if isinstance(envelope.get("from"), dict) else {}
    source_id = from_ref.get("entity_id")
    if not source_id:
        return None

    try:
        from models.entity import Entity
        from models.invocation import InvocationStatus, InvocationStep, InvocationTrace
        from services.federation_community import peer_entity_id

        if db.get(Entity, source_id) is None:
            return None

        target_id = local_target_entity_id
        if target_id and db.get(Entity, target_id) is None:
            target_id = None
        if not target_id:
            fallback = peer_entity_id(peer["node_id"])
            if db.get(Entity, fallback) is not None:
                target_id = fallback
        if not target_id:
            return None

        trace = InvocationTrace(
            initiator_id=source_id,
            model_provider="peer_route",
            status=InvocationStatus.completed,
        )
        db.add(trace)
        db.flush()

        payload = envelope.get("payload") if isinstance(envelope.get("payload"), dict) else {}
        remote_refs = remote.get("refs") if isinstance(remote.get("refs"), dict) else {}
        step = InvocationStep(
            trace_id=trace.id,
            step_order=1,
            source_entity_id=source_id,
            target_entity_id=target_id,
            action="routes_to_peer",
            metadata_={
                "dialogue_id": envelope.get("dialogue_id"),
                "dialogue_kind": envelope.get("kind"),
                "peer_node_id": peer["node_id"],
                "peer_base_url": peer.get("public_base_url") or peer["base_url"],
                "peer_invocation_trace_id": remote_refs.get("invocation_trace_id"),
                "input": payload.get("input"),
            },
        )
        db.add(step)
        db.commit()
        return trace.id
    except Exception as exc:
        logger.debug("peer route trace stub skipped: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
        return None


def try_peer_route_dialogue(
    db,
    envelope: dict[str, Any],
    *,
    resolve_target,
) -> dict[str, Any] | None:
    """
    If envelope targets another node's entity, forward over HTTPS to trusted peer.
    `resolve_target` is callable(db, to_ref) -> Entity | None.
    """
    to_ref = envelope.get("to") if isinstance(envelope.get("to"), dict) else {}
    entity_id = to_ref.get("entity_id")
    local_target_entity_id = entity_id
    if entity_id and db is not None:
        try:
            from services.federation_entity_mirror import resolve_mirror_for_dialogue

            mirror = resolve_mirror_for_dialogue(db, entity_id)
            if mirror:
                to_ref = {
                    **to_ref,
                    "node_id": mirror["home_node_id"],
                    "portable_id": mirror.get("portable_id") or to_ref.get("portable_id"),
                    "entity_id": mirror.get("remote_entity_id"),
                }
                envelope = {**envelope, "to": to_ref}
                payload = dict(envelope.get("payload") or {})
                payload["route_peer"] = True
                envelope = {**envelope, "payload": payload}
        except Exception:
            pass

    target = resolve_target(db, to_ref)
    route, peer_node = should_route_to_peer(
        envelope,
        target_resolved_locally=target is not None,
    )
    if not route or not peer_node:
        return None

    peer = resolve_runtime_peer(db, peer_node)
    if peer is None:
        from services.entity_dialogue import _response_envelope

        return _response_envelope(
            envelope,
            status="rejected",
            errors=[
                f"to.node_id {peer_node} not routable (add trust config or register discovered peer with base_url)"
            ],
        )

    try:
        remote = forward_dialogue_to_peer(peer["base_url"], envelope)
    except Exception as exc:
        logger.warning("peer dialogue route failed %s: %s", peer["base_url"], exc)
        from services.entity_dialogue import _response_envelope

        return _response_envelope(
            envelope,
            status="rejected",
            errors=[f"peer dialogue failed: {exc}"],
            bindings={"peer_dialogue": f"{peer['base_url']}{FEDERATION_DIALOGUE_PATH}"},
        )

    local_trace_id = record_peer_route_trace_stub(
        db,
        envelope,
        remote,
        peer=peer,
        local_target_entity_id=local_target_entity_id,
    )
    originator_exchange_id = record_peer_route_exchange_on_originator(
        db,
        envelope,
        remote,
        peer=peer,
        local_trace_id=local_trace_id,
        local_target_entity_id=local_target_entity_id,
    )
    wrapped = wrap_peer_route_response(
        envelope,
        remote,
        peer=peer,
        local_trace_id=local_trace_id,
    )
    if originator_exchange_id:
        refs = dict(wrapped.get("refs") or {})
        refs.setdefault("originator_exchange_id", originator_exchange_id)
        wrapped["refs"] = refs
        result = dict(wrapped.get("result") or {})
        result["originator_exchange_settled"] = True
        wrapped["result"] = result
    return wrapped
