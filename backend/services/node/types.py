from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class NodeProfile:
    node_id: str
    entity_id: str
    node_type: str
    did: str | None = None
    public_key: str | None = None
    base_url: str | None = None
    p2p_address: str | None = None
    health_url: str | None = None
    status: str = "registered"
    protocol_version: str = "pocp-node-v0.1"
    last_heartbeat_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class PublicNodeEndpoint:
    node_id: str
    entity_id: str
    base_url: str
    manifest_url: str
    health_url: str
    capabilities_url: str
    invoke_url: str
    proof_url: str
    settlement_ack_url: str
    status: str = "registered"
