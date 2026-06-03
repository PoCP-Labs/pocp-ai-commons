from __future__ import annotations

from typing import Any, Protocol


class EntityCatalogRegistry(Protocol):
    """Open-core entity catalog boundary — persistence in services/entity_catalog.py.

    Frozen CI-1 IDs: ``services.entity.schemas.INFRASTRUCTURE_ENTITY_IDS``.
    Node handoff (CI-2): ``NODE_ELIGIBLE_INFRASTRUCTURE_IDS`` → ``catalog_node_specs()``.
    """

    def audit(self) -> dict[str, Any]:
        """Summarize ontology coverage, capabilities, and ownership gaps.

        Expected keys include ``missing_types``, ``missing_capabilities``,
        ``entity_count``, ``capability_count`` (≥ ``REGISTRY_MIN_CAPABILITY_COUNT``).
        """
        ...

    def ensure(self) -> dict[str, Any]:
        """Idempotently register infrastructure entities, capabilities, and node profiles.

        When not skipped, returns ``node_profiles_created`` after Layer-2 bootstrap.
        """
        ...
