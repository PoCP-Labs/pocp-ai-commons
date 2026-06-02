from __future__ import annotations
from dataclasses import dataclass
from backend.services.cip.types import NodeProfileData

@dataclass
class CIPNodeManifest:
    node_id: str
    entity_id: str
    base_url: str
    public_key: str
    health_url: str
    capabilities_url: str
    protocol_version: str

class CIPNodeManifestService:
    def build_manifest(self, node: NodeProfileData) -> CIPNodeManifest:
        if not node.base_url or not node.public_key:
            raise ValueError("base_url and public_key are required.")
        base = node.base_url.rstrip("/")
        return CIPNodeManifest(
            node_id=node.node_id,
            entity_id=node.entity_id,
            base_url=base,
            public_key=node.public_key,
            health_url=f"{base}/pocp/health",
            capabilities_url=f"{base}/pocp/capabilities",
            protocol_version=node.protocol_version,
        )
