from __future__ import annotations

import uuid

from services.cip.types import CapabilityData


class CIPCapabilityRegistry:
    """In-memory capability registry."""

    def __init__(self) -> None:
        self.capabilities: dict[str, CapabilityData] = {}

    def publish(
        self,
        entity_id: str,
        node_id: str | None,
        capability_type: str,
        name: str,
        unit: str,
        price: dict[str, float] | None = None,
    ) -> CapabilityData:
        capability = CapabilityData(
            capability_id=f"cap_{uuid.uuid4().hex[:16]}",
            entity_id=entity_id,
            node_id=node_id,
            capability_type=capability_type,
            name=name,
            unit=unit,
            price=price or {},
        )
        self.capabilities[capability.capability_id] = capability
        return capability

    def search(self, capability_type: str) -> list[CapabilityData]:
        return [cap for cap in self.capabilities.values() if cap.capability_type == capability_type]
