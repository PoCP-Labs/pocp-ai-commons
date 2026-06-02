"""Persist ProtocolEvent overlay to database (v0.2)."""

from __future__ import annotations

import logging
import os
from typing import Any

from services.network.protocol_bridge import event_batch_to_dict, protocol_event_to_dict
from services.network.types import EventBatch, ProtocolEvent

logger = logging.getLogger(__name__)


def overlay_persist_enabled() -> bool:
    return os.getenv("POCP_OVERLAY_PERSIST", "true").lower() in ("true", "1", "yes", "on")


def _session():
    from database import SessionLocal

    return SessionLocal()


def persist_overlay_event(event: ProtocolEvent) -> None:
    if not overlay_persist_enabled():
        return
    from models.protocol_overlay import OverlayEventMempoolStatus, ProtocolOverlayEvent

    db = _session()
    try:
        existing = db.get(ProtocolOverlayEvent, event.event_id)
        if existing is not None:
            return
        row = ProtocolOverlayEvent(
            event_id=event.event_id,
            event_type=event.event_type,
            entity_id=event.entity_id,
            node_id=event.node_id,
            payload=event.payload,
            payload_hash=event.payload_hash,
            previous_event_hash=event.previous_event_hash,
            event_hash=event.event_hash(),
            event_timestamp=event.timestamp,
            mempool_status=OverlayEventMempoolStatus.pending,
        )
        db.add(row)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("overlay persist event failed: %s", exc)
    finally:
        db.close()


def persist_overlay_batch(batch: EventBatch, events: list[ProtocolEvent]) -> None:
    if not overlay_persist_enabled():
        return
    from models.protocol_overlay import OverlayEventMempoolStatus, ProtocolOverlayBatch, ProtocolOverlayEvent

    meta = batch.metadata or {}
    db = _session()
    try:
        db.add(
            ProtocolOverlayBatch(
                batch_id=batch.batch_id,
                event_count=len(events),
                event_hashes=batch.event_hashes,
                event_merkle_root=batch.event_merkle_root,
                merkle_root_hex=meta.get("merkle_root_hex"),
                previous_batch_hash=batch.previous_batch_hash,
                batch_hash=batch.batch_hash(),
                created_by_node_id=batch.created_by_node_id,
                batch_timestamp=batch.timestamp,
                metadata_=meta,
            )
        )
        event_ids = [e.event_id for e in events]
        if event_ids:
            (
                db.query(ProtocolOverlayEvent)
                .filter(ProtocolOverlayEvent.event_id.in_(event_ids))
                .update(
                    {
                        ProtocolOverlayEvent.mempool_status: OverlayEventMempoolStatus.sealed,
                        ProtocolOverlayEvent.batch_id: batch.batch_id,
                    },
                    synchronize_session=False,
                )
            )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("overlay persist batch failed: %s", exc)
    finally:
        db.close()


def clear_persisted_overlay() -> None:
    """Test helper — wipe persisted overlay tables."""
    if not overlay_persist_enabled():
        return
    from models.protocol_overlay import ProtocolOverlayBatch, ProtocolOverlayEvent

    db = _session()
    try:
        db.query(ProtocolOverlayEvent).delete()
        db.query(ProtocolOverlayBatch).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def count_pending_in_db() -> int:
    if not overlay_persist_enabled():
        return 0
    from models.protocol_overlay import OverlayEventMempoolStatus, ProtocolOverlayEvent

    db = _session()
    try:
        return (
            db.query(ProtocolOverlayEvent)
            .filter(ProtocolOverlayEvent.mempool_status == OverlayEventMempoolStatus.pending)
            .count()
        )
    except Exception:
        return 0
    finally:
        db.close()


def count_batches_in_db() -> int:
    if not overlay_persist_enabled():
        return 0
    from models.protocol_overlay import ProtocolOverlayBatch

    db = _session()
    try:
        return db.query(ProtocolOverlayBatch).count()
    except Exception:
        return 0
    finally:
        db.close()


def last_batch_from_db() -> dict[str, Any] | None:
    if not overlay_persist_enabled():
        return None
    from models.protocol_overlay import ProtocolOverlayBatch

    db = _session()
    try:
        row = (
            db.query(ProtocolOverlayBatch)
            .order_by(ProtocolOverlayBatch.created_at.desc())
            .first()
        )
        if row is None:
            return None
        return {
            "batch_id": row.batch_id,
            "event_hashes": row.event_hashes or [],
            "event_merkle_root": row.event_merkle_root,
            "merkle_root_hex": row.merkle_root_hex,
            "previous_batch_hash": row.previous_batch_hash,
            "created_by_node_id": row.created_by_node_id,
            "batch_hash": row.batch_hash,
            "timestamp": row.batch_timestamp,
            "event_count": row.event_count,
            "metadata": row.metadata_ or {},
        }
    except Exception:
        return None
    finally:
        db.close()


def list_events_from_db(
    *,
    mempool_status: str | None = None,
    event_type: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    if not overlay_persist_enabled():
        return []
    from models.protocol_overlay import OverlayEventMempoolStatus, ProtocolOverlayEvent

    db = _session()
    try:
        q = db.query(ProtocolOverlayEvent).order_by(ProtocolOverlayEvent.created_at.desc())
        if mempool_status:
            q = q.filter(
                ProtocolOverlayEvent.mempool_status == OverlayEventMempoolStatus(mempool_status)
            )
        if event_type:
            q = q.filter(ProtocolOverlayEvent.event_type == event_type)
        rows = q.limit(limit).all()
        return [_event_row_to_dict(r) for r in rows]
    except Exception:
        return []
    finally:
        db.close()


def ingest_gossip_events(
    *,
    source_node_id: str,
    events: list[dict[str, Any]],
    batch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Import remote overlay events/batch from trusted peer gossip."""
    if not overlay_persist_enabled():
        return {
            "imported": 0,
            "skipped": len(events),
            "batch_imported": False,
            "reason": "POCP_OVERLAY_PERSIST disabled",
        }

    from models.protocol_overlay import OverlayEventMempoolStatus, ProtocolOverlayBatch, ProtocolOverlayEvent

    batch_id = (batch or {}).get("batch_id")
    sealed_status = OverlayEventMempoolStatus.sealed if batch_id else OverlayEventMempoolStatus.pending

    db = _session()
    imported = 0
    skipped = 0
    batch_imported = False
    try:
        for doc in events:
            if doc.get("schema") and doc.get("schema") != "pocp.protocol_event.v0.1":
                skipped += 1
                continue
            event_id = doc.get("event_id")
            if not event_id:
                skipped += 1
                continue
            if db.get(ProtocolOverlayEvent, event_id) is not None:
                skipped += 1
                continue
            db.add(
                ProtocolOverlayEvent(
                    event_id=event_id,
                    event_type=doc.get("event_type") or "ProtocolGossip",
                    entity_id=doc.get("entity_id"),
                    node_id=doc.get("node_id") or source_node_id,
                    payload=doc.get("payload") if isinstance(doc.get("payload"), dict) else {},
                    payload_hash=doc.get("payload_hash"),
                    previous_event_hash=doc.get("previous_event_hash"),
                    event_hash=doc.get("event_hash") or "",
                    event_timestamp=doc.get("timestamp"),
                    mempool_status=sealed_status,
                    batch_id=batch_id,
                )
            )
            imported += 1

        if batch and batch.get("batch_id"):
            bid = batch["batch_id"]
            if db.get(ProtocolOverlayBatch, bid) is None:
                meta = batch.get("metadata") if isinstance(batch.get("metadata"), dict) else {}
                db.add(
                    ProtocolOverlayBatch(
                        batch_id=bid,
                        event_count=int(batch.get("event_count") or len(events)),
                        event_hashes=batch.get("event_hashes") or [],
                        event_merkle_root=batch.get("event_merkle_root") or "",
                        merkle_root_hex=batch.get("merkle_root_hex") or meta.get("merkle_root_hex"),
                        previous_batch_hash=batch.get("previous_batch_hash"),
                        batch_hash=batch.get("batch_hash") or "",
                        created_by_node_id=batch.get("created_by_node_id") or source_node_id,
                        batch_timestamp=batch.get("timestamp"),
                        metadata_={
                            **meta,
                            "gossip_source_node_id": source_node_id,
                        },
                    )
                )
                batch_imported = True

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("ingest_gossip_events failed: %s", exc)
        raise
    finally:
        db.close()

    return {
        "schema": "pocp.overlay_gossip_receive.v0.1",
        "source_node_id": source_node_id,
        "imported": imported,
        "skipped": skipped,
        "batch_imported": batch_imported,
        "batch_id": batch_id,
    }


def _event_row_to_dict(row) -> dict[str, Any]:
    from services.network.protocol_bridge import PROTOCOL_EVENT_SCHEMA

    return {
        "schema": PROTOCOL_EVENT_SCHEMA,
        "event_id": row.event_id,
        "event_type": row.event_type,
        "entity_id": row.entity_id,
        "node_id": row.node_id,
        "payload": row.payload or {},
        "payload_hash": row.payload_hash,
        "previous_event_hash": row.previous_event_hash,
        "event_hash": row.event_hash,
        "timestamp": row.event_timestamp,
        "mempool_status": row.mempool_status.value,
        "batch_id": row.batch_id,
    }
