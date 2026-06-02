from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import hashlib, json, uuid

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def canonical_hash(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, default=str)
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()

@dataclass
class NetworkPeer:
    peer_id: str
    node_id: str
    entity_id: str
    roles: list[str] = field(default_factory=list)
    addresses: list[str] = field(default_factory=list)
    public_key: str | None = None
    status: str = "connected"

@dataclass
class ProtocolEvent:
    event_id: str
    event_type: str
    entity_id: str | None = None
    node_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    payload_hash: str | None = None
    previous_event_hash: str | None = None
    timestamp: str = field(default_factory=now_iso)
    nonce: str | None = None
    signature: str | None = None

    @classmethod
    def create(cls, event_type: str, payload: dict[str, Any], entity_id: str | None = None,
               node_id: str | None = None, previous_event_hash: str | None = None) -> "ProtocolEvent":
        return cls(
            event_id=f"evt_{uuid.uuid4().hex[:16]}",
            event_type=event_type,
            entity_id=entity_id,
            node_id=node_id,
            payload=payload,
            payload_hash=canonical_hash(payload),
            previous_event_hash=previous_event_hash,
            nonce=f"nonce_{uuid.uuid4().hex[:12]}",
        )

    def event_hash(self) -> str:
        return canonical_hash({
            "event_id": self.event_id,
            "event_type": self.event_type,
            "entity_id": self.entity_id,
            "node_id": self.node_id,
            "payload_hash": self.payload_hash,
            "previous_event_hash": self.previous_event_hash,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
        })

@dataclass
class EventBatch:
    batch_id: str
    event_hashes: list[str]
    event_merkle_root: str
    previous_batch_hash: str | None = None
    created_by_node_id: str | None = None
    timestamp: str = field(default_factory=now_iso)
    signature: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def batch_hash(self) -> str:
        return canonical_hash({
            "batch_id": self.batch_id,
            "event_merkle_root": self.event_merkle_root,
            "merkle_root_hex": (self.metadata or {}).get("merkle_root_hex"),
            "previous_batch_hash": self.previous_batch_hash,
            "created_by_node_id": self.created_by_node_id,
            "timestamp": self.timestamp,
        })

@dataclass
class ConfirmationStatus:
    event_id: str
    level: int
    label: str
    finalized: bool = False
    details: dict[str, Any] = field(default_factory=dict)
