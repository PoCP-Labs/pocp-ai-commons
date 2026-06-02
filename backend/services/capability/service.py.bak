from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import uuid

@dataclass
class Capability:
    capability_id: str
    entity_id: str
    node_id: str | None
    capability_type: str
    name: str
    unit: str
    price: dict[str, float] = field(default_factory=dict)
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    verification_method: str = "human_review"
    risk_level: str = "low"
    availability: str = "available"
    version: str = "v0.1"

class CapabilityService:
    def publish(self, entity_id: str, capability_type: str, name: str, unit: str,
                node_id: str | None = None, price: dict[str, float] | None = None,
                verification_method: str = "human_review") -> Capability:
        return Capability(
            capability_id=f"cap_{uuid.uuid4().hex[:16]}",
            entity_id=entity_id, node_id=node_id, capability_type=capability_type,
            name=name, unit=unit, price=price or {}, verification_method=verification_method,
        )
