from __future__ import annotations

from services.cip.capability.registry import CIPCapabilityRegistry
from services.cip.types import CapabilityData


class CIPDiscoveryService:
    """Reference discovery service."""

    def __init__(self, capability_registry: CIPCapabilityRegistry) -> None:
        self.capability_registry = capability_registry

    def discover(self, capability_type: str) -> list[CapabilityData]:
        return self.capability_registry.search(capability_type)
