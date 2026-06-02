from __future__ import annotations
import uuid
from backend.services.cip.types import NodeProfileData

class CIPNodeRegistry:
    def __init__(self) -> None:
        self.nodes: dict[str, NodeProfileData] = {}

    def register_node(self, entity_id: str, node_type: str, public_key: str | None = None, base_url: str | None = None, p2p_address: str | None = None) -> NodeProfileData:
        health_url = f"{base_url.rstrip('/')}/pocp/health" if base_url else None
        node = NodeProfileData(
            node_id=f"node_{uuid.uuid4().hex[:16]}",
            entity_id=entity_id,
            node_type=node_type,
            public_key=public_key,
            base_url=base_url,
            p2p_address=p2p_address,
            health_url=health_url,
        )
        self.nodes[node.node_id] = node
        return node

    def list(self) -> list[NodeProfileData]:
        return list(self.nodes.values())
