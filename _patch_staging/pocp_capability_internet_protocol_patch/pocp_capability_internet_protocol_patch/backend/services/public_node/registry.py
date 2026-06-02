from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from backend.services.node.types import NodeProfile, PublicNodeEndpoint

@dataclass
class PublicNodeRecord:
    profile: NodeProfile
    endpoint: PublicNodeEndpoint | None = None
    capabilities: list[str] = field(default_factory=list)
    last_seen_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

class PublicNodeRegistry:
    def __init__(self) -> None:
        self._records: dict[str, PublicNodeRecord] = {}

    def register(self, profile: NodeProfile, endpoint: PublicNodeEndpoint | None = None,
                 capabilities: list[str] | None = None) -> PublicNodeRecord:
        record = PublicNodeRecord(profile=profile, endpoint=endpoint,
                                  capabilities=capabilities or [],
                                  last_seen_at=datetime.now(timezone.utc))
        self._records[profile.node_id] = record
        return record

    def discover(self, capability_type: str | None = None) -> list[PublicNodeRecord]:
        records = list(self._records.values())
        return [r for r in records if not capability_type or capability_type in r.capabilities]
