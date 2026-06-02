"""In-process overlay runtime — mempool + last sealed batch (v0.1 pilot)."""

from __future__ import annotations

from typing import Any

from services.compute_registry import compute_status_manifest
from services.network.confirmation import ConfirmationService
from services.network.event_batch import EventBatchService
from services.network.mempool import PoCPMempool
from services.merkle_canonical import MERKLE_ALGORITHM
from services.network.protocol_bridge import event_batch_to_dict, protocol_event_to_dict
from services.network.types import EventBatch, ProtocolEvent

_mempool = PoCPMempool()
_batcher = EventBatchService()
_confirmations = ConfirmationService()
_last_batch: EventBatch | None = None
_batches: list[EventBatch] = []
_recent_events: list[dict[str, Any]] = []
_MAX_RECENT_EVENTS = 48


def overlay_mempool() -> PoCPMempool:
    return _mempool


def _pending_counts_by_type() -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in _mempool.pending():
        counts[event.event_type] = counts.get(event.event_type, 0) + 1
    return counts


def recent_overlay_events(
    event_type: str | None = None,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    items = _recent_events
    if event_type:
        items = [e for e in items if e.get("event_type") == event_type]
    return list(reversed(items[-limit:]))


def overlay_status() -> dict[str, Any]:
    from services.network.persistence import (
        count_batches_in_db,
        count_pending_in_db,
        last_batch_from_db,
        list_events_from_db,
        overlay_persist_enabled,
    )

    node_id = compute_status_manifest().get("node_id", "unknown")
    pending_by_type = _pending_counts_by_type()
    persist = overlay_persist_enabled()
    mempool_size = len(_mempool.pending())
    batch_count = len(_batches)
    last_batch = event_batch_to_dict(_last_batch) if _last_batch else None
    recent = recent_overlay_events(limit=8)

    if persist:
        db_pending = count_pending_in_db()
        if db_pending > mempool_size:
            mempool_size = db_pending
        batch_count = max(batch_count, count_batches_in_db())
        if last_batch is None:
            last_batch = last_batch_from_db()
        db_recent = list_events_from_db(limit=8)
        if db_recent:
            recent = db_recent

    return {
        "schema": "pocp.network_overlay_status.v0.2" if persist else "pocp.network_overlay_status.v0.1",
        "node_id": node_id,
        "mempool_size": mempool_size,
        "pending_by_type": pending_by_type,
        "batch_count": batch_count,
        "last_batch": last_batch,
        "merkle_algorithm": MERKLE_ALGORITHM,
        "ledger_compatible": True,
        "persist_enabled": persist,
        "transport": "db_v0.2" if persist else "in_process_v0.1",
        "physical_network": "none",
        "recent_events": recent,
    }


def federation_overlay_status() -> dict[str, Any]:
    """Federation slice of overlay — pending + recent FederatedProofOffered events."""
    base = overlay_status()
    fed_type = "FederatedProofOffered"
    return {
        **base,
        "schema": "pocp.federation_overlay_status.v0.1",
        "federation": {
            "pending_federation_offers": base["pending_by_type"].get(fed_type, 0),
            "recent_federation_events": recent_overlay_events(fed_type, limit=8),
            "relay_api": "/api/v1/federation/overlay/relay",
            "dialogue_api": "/api/v1/federation/dialogue",
        },
    }


def enqueue_event(event: ProtocolEvent) -> dict[str, Any]:
    from services.network.persistence import persist_overlay_event

    doc = protocol_event_to_dict(event)
    _mempool.add(event)
    _recent_events.append(doc)
    if len(_recent_events) > _MAX_RECENT_EVENTS:
        del _recent_events[: len(_recent_events) - _MAX_RECENT_EVENTS]
    persist_overlay_event(event)
    return doc


def seal_batch(*, created_by_node_id: str | None = None) -> dict[str, Any]:
    global _last_batch
    events = _mempool.drain()
    if not events:
        return {"sealed": False, "reason": "mempool_empty", "events": []}
    prev = _last_batch.batch_hash() if _last_batch else None
    batch = _batcher.create_batch(
        events,
        previous_batch_hash=prev,
        created_by_node_id=created_by_node_id,
    )
    _last_batch = batch
    _batches.append(batch)
    from services.network.persistence import persist_overlay_batch

    persist_overlay_batch(batch, events)
    event_docs = [protocol_event_to_dict(e) for e in events]
    batch_doc = event_batch_to_dict(batch)
    gossip_result = None
    from services.network.gossip import gossip_on_seal_enabled, push_gossip_to_trusted_peers

    if gossip_on_seal_enabled():
        gossip_result = push_gossip_to_trusted_peers(events=event_docs, batch=batch_doc)

    return {
        "sealed": True,
        "batch": batch_doc,
        "event_count": len(events),
        "events": event_docs,
        "gossip": gossip_result,
    }


def reset_overlay_runtime() -> None:
    """Test helper — clear mempool and batches."""
    global _last_batch
    _mempool.drain()
    _batches.clear()
    _last_batch = None
    _recent_events.clear()
    from services.network.persistence import clear_persisted_overlay

    clear_persisted_overlay()
