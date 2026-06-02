"""Overlay peer gossip — push sealed batches to trusted federation peers (v0.2b)."""

from __future__ import annotations

import logging
import os
from typing import Any

from services.compute_registry import compute_status_manifest
from services.federation_peers import _post_json
from services.network.protocol_bridge import PROTOCOL_EVENT_SCHEMA
from services.trust_config import load_trusted_nodes, trusted_nodes_map

logger = logging.getLogger(__name__)

GOSSIP_SCHEMA = "pocp.overlay_gossip.v0.1"
RECEIVE_PATH = "/api/v1/intelligence/network/overlay/gossip/receive"


def gossip_enabled() -> bool:
    return os.getenv("POCP_OVERLAY_GOSSIP", "true").lower() in ("true", "1", "yes", "on")


def gossip_on_seal_enabled() -> bool:
    return os.getenv("POCP_OVERLAY_GOSSIP_ON_SEAL", "false").lower() in ("true", "1", "yes", "on")


def _local_node_id() -> str:
    return compute_status_manifest().get("node_id") or os.getenv("POCP_NODE_ID", "unknown")


def build_gossip_payload(
    *,
    events: list[dict[str, Any]],
    batch: dict[str, Any] | None = None,
    source_node_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": GOSSIP_SCHEMA,
        "source_node_id": source_node_id or _local_node_id(),
        "events": events,
        "batch": batch,
    }


def push_gossip_to_peer(base_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{RECEIVE_PATH}"
    try:
        result = _post_json(url, payload)
        return {"ok": True, "base_url": base_url, "result": result}
    except Exception as exc:
        logger.warning("gossip push failed %s: %s", base_url, exc)
        return {"ok": False, "base_url": base_url, "error": str(exc)[:500]}


def push_gossip_to_trusted_peers(
    *,
    events: list[dict[str, Any]],
    batch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """POST sealed overlay batch to all POCP_TRUSTED_NODES."""
    if not gossip_enabled():
        return {"ran": False, "reason": "POCP_OVERLAY_GOSSIP disabled"}

    peers = load_trusted_nodes()
    if not peers:
        return {"ran": False, "reason": "no_trusted_peers"}

    payload = build_gossip_payload(events=events, batch=batch)
    results = [push_gossip_to_peer(peer.base_url, payload) for peer in peers]
    ok_count = sum(1 for r in results if r.get("ok"))
    return {
        "ran": True,
        "schema": "pocp.overlay_gossip_push.v0.1",
        "source_node_id": payload["source_node_id"],
        "peer_count": len(peers),
        "peers_ok": ok_count,
        "peers_failed": len(peers) - ok_count,
        "results": results,
    }


def receive_gossip_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Ingest gossip from a trusted peer — idempotent on event_id / batch_id."""
    if payload.get("schema") != GOSSIP_SCHEMA:
        raise ValueError(f"Invalid gossip schema: {payload.get('schema')}")

    source_node_id = payload.get("source_node_id")
    if not source_node_id:
        raise ValueError("source_node_id required")

    trusted = trusted_nodes_map()
    if source_node_id not in trusted:
        raise ValueError(f"Untrusted gossip source_node_id: {source_node_id}")

    events = payload.get("events")
    if not isinstance(events, list):
        raise ValueError("events must be a list")

    batch = payload.get("batch") if isinstance(payload.get("batch"), dict) else None
    from services.network.persistence import ingest_gossip_events

    return ingest_gossip_events(source_node_id=source_node_id, events=events, batch=batch)
