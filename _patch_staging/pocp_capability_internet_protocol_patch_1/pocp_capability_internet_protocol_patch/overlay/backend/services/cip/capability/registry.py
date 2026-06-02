from __future__ import annotations
import uuid
from backend.services.cip.types import CapabilityData

class CIPCapabilityRegistry:
    def __init__(self) -> None:
        self.capabilities: dict[str, CapabilityData] = {}

    def publish(self, entity_id: str, node_id: str | None, capability_type: str, name: str, unit: str, price: dict[str, float] | None = None, verification_method: str = "human_review") -> CapabilityData:
        cap = CapabilityData(
            capability_id=f"cap_{uuid.uuid4().hex[:16]}",
            entity_id=entity_id,
            node_id=node_id,
            capability_type=capability_type,
            name=name,
            unit=unit,
            price=price or {},
            verification_method=verification_method,
        )
        self.capabilities[cap.capability_id] = cap
        return cap

    def search(self, capability_type: str | None = None) -> list[CapabilityData]:
        values = list(self.capabilities.values())
        return [c for c in values if c.capability_type == capability_type] if capability_type else values
