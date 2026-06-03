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
    bindings = dict(remote.get("bindings") or {})
    bindings["peer_dialogue"] = f"{peer['base_url']}{FEDERATION_DIALOGUE_PATH}"
    remote["bindings"] = bindings
    return remote


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

    return wrap_peer_route_response(envelope, remote, peer=peer)
