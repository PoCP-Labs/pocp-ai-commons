from __future__ import annotations

from typing import Any, Protocol

from services.node.schemas import (
    NodeProfileSchema,
    PublicNodeEndpointSchema,
    WellKnownInstanceManifestSchema,
    build_instance_endpoints,
    validate_node_profile,
    validate_node_type,
    validate_well_known_entity,
    validate_well_known_instance,
)


class NodeProfileRegistry(Protocol):
    """Open-core node profile boundary — persistence lives in services/node/store.py."""

    def register(
        self,
        *,
        entity_id: str,
        node_type: str,
        base_url: str | None = None,
        public_key: str | None = None,
    ) -> NodeProfileSchema:
        ...

    def get_by_entity(self, entity_id: str) -> NodeProfileSchema | None:
        ...

    def public_endpoint(self, profile: NodeProfileSchema) -> PublicNodeEndpointSchema | None:
        ...


class WellKnownManifestBuilder(Protocol):
    """Instance-level discovery manifest — wire target: GET /.well-known/pocp-node.json."""

    def build_instance_manifest(self) -> WellKnownInstanceManifestSchema | dict[str, Any]:
        ...


__all__ = [
    "NodeProfileRegistry",
    "WellKnownManifestBuilder",
    "build_instance_endpoints",
    "validate_node_profile",
    "validate_node_type",
    "validate_well_known_entity",
    "validate_well_known_instance",
]
