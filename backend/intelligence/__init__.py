"""PoCP Intelligence Capability Layer."""

from intelligence.kernel import CapabilityLayer, capability_layer
from intelligence.protocol import (
    CAPABILITY_LAYER_VERSION,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    UNIFIED_PRINCIPLE,
    UNIFIED_PRINCIPLE_ZH,
    CapabilityModule,
    entity_can_contribute,
)

__all__ = [
    "CapabilityLayer",
    "capability_layer",
    "CapabilityModule",
    "CAPABILITY_LAYER_VERSION",
    "PROTOCOL_NAME",
    "PROTOCOL_VERSION",
    "UNIFIED_PRINCIPLE",
    "UNIFIED_PRINCIPLE_ZH",
    "entity_can_contribute",
]
