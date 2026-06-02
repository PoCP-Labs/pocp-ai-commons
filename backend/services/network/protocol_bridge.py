"""Bridge L2 Entity Dialogue ↔ L1.5 ProtocolEvent overlay."""

from __future__ import annotations

from typing import Any

from services.network.types import ProtocolEvent

PROTOCOL_EVENT_SCHEMA = "pocp.protocol_event.v0.1"

DIALOGUE_TO_EVENT_TYPE: dict[str, str] = {
    "invoke": "InvocationCreated",
    "attest": "VerificationCompleted",
    "submit": "ProofSubmitted",
    "federation_offer": "FederatedProofOffered",
    "finalize_notice": "SettlementExecuted",
    "quote": "ExchangeQuoted",
}

DIALOGUE_KINDS_EMITTING_OVERLAY = frozenset(
    {"invoke", "attest", "submit", "federation_offer", "finalize_notice", "broadcast", "quote"}
)


def protocol_event_from_dialogue(envelope: dict[str, Any]) -> ProtocolEvent | None:
    """Map a dialogue envelope to a ProtocolEvent when the kind is overlay-eligible."""
    kind = envelope.get("kind")
    if kind not in DIALOGUE_KINDS_EMITTING_OVERLAY:
        return None

    from_ref = envelope.get("from") if isinstance(envelope.get("from"), dict) else {}
    payload = envelope.get("payload") if isinstance(envelope.get("payload"), dict) else {}
    refs = envelope.get("refs") if isinstance(envelope.get("refs"), dict) else {}

    if kind == "broadcast":
        event_type = payload.get("event_type") or "ProtocolBroadcast"
        body = payload.get("event_payload") or payload
    else:
        event_type = DIALOGUE_TO_EVENT_TYPE.get(kind, "ProtocolDialogue")
        body = {
            "dialogue_id": envelope.get("dialogue_id"),
            "dialogue_kind": kind,
            "payload": payload,
            "refs": refs,
        }

    return ProtocolEvent.create(
        event_type,
        body,
        entity_id=from_ref.get("entity_id"),
        node_id=from_ref.get("node_id"),
        previous_event_hash=refs.get("previous_event_hash"),
    )


def protocol_event_to_dict(event: ProtocolEvent) -> dict[str, Any]:
    return {
        "schema": PROTOCOL_EVENT_SCHEMA,
        "event_id": event.event_id,
        "event_type": event.event_type,
        "entity_id": event.entity_id,
        "node_id": event.node_id,
        "payload": event.payload,
        "payload_hash": event.payload_hash,
        "previous_event_hash": event.previous_event_hash,
        "event_hash": event.event_hash(),
        "timestamp": event.timestamp,
    }


def event_batch_to_dict(batch: Any) -> dict[str, Any]:
    meta = getattr(batch, "metadata", None) or {}
    return {
        "batch_id": batch.batch_id,
        "event_hashes": batch.event_hashes,
        "event_merkle_root": batch.event_merkle_root,
        "merkle_root_hex": meta.get("merkle_root_hex"),
        "merkle_algorithm": meta.get("merkle_algorithm"),
        "ledger_compatible": meta.get("ledger_compatible", True),
        "previous_batch_hash": batch.previous_batch_hash,
        "created_by_node_id": batch.created_by_node_id,
        "batch_hash": batch.batch_hash(),
        "timestamp": batch.timestamp,
    }
