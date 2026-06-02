"""Capability registry, seeds, and bootstrap for Phase A kernel."""

from services.capability.bootstrap import (
    audit_registry,
    ensure_capability_registry,
    ensure_demo_tool_for_registry,
    ensure_skill_capability,
    seed_platform_capabilities,
)
from services.capability.seeds import (
    CAPABILITY_SEEDS,
    REGISTRY_MIN_COUNT,
    expected_capability_ids,
)

__all__ = [
    "CAPABILITY_SEEDS",
    "REGISTRY_MIN_COUNT",
    "audit_registry",
    "ensure_capability_registry",
    "ensure_demo_tool_for_registry",
    "ensure_skill_capability",
    "expected_capability_ids",
    "seed_platform_capabilities",
]
