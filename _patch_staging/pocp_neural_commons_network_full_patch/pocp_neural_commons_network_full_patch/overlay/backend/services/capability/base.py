from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class CapabilityDescriptor:
    capability_id: str
    entity_id: str
    capability_type: str
    name: str
    unit: str
    price_model: str = "fixed"
    base_price: float = 0.0
    accepted_units: list[str] = field(default_factory=lambda: ["AIC"])
    verification_method: str = "human_review"
    availability: str = "available"
    reputation_score: float = 0.0
    risk_level: str = "low"
    metadata: dict[str, Any] = field(default_factory=dict)


class CapabilityRegistry(Protocol):
    def register(self, capability: CapabilityDescriptor) -> CapabilityDescriptor:
        ...

    def search(self, capability_type: str | None = None) -> list[CapabilityDescriptor]:
        ...
