from __future__ import annotations
import uuid
from datetime import datetime, timezone
from .types import NodeProfile, PublicNodeEndpoint

class NodeProfileService:
    def register_node(self, entity_id: str, node_type: str, public_key: str | None = None,
                      base_url: str | None = None, p2p_address: str | None = None) -> NodeProfile:
        node_id = f"node_{uuid.uuid4().hex[:16]}"
        health_url = f"{base_url.rstrip('/')}/pocp/health" if base_url else None
        return NodeProfile(
            node_id=node_id, entity_id=entity_id, node_type=node_type,
            did=f"did:pocp:{entity_id}", public_key=public_key,
            base_url=base_url, p2p_address=p2p_address, health_url=health_url,
            last_heartbeat_at=datetime.now(timezone.utc),
        )

    def public_endpoint(self, profile: NodeProfile) -> PublicNodeEndpoint | None:
        if not profile.base_url:
            return None
        base_url = profile.base_url.rstrip("/")
        return PublicNodeEndpoint(
            node_id=profile.node_id, entity_id=profile.entity_id, base_url=base_url,
            manifest_url=f"{base_url}/.well-known/pocp-node.json",
            health_url=f"{base_url}/pocp/health",
            capabilities_url=f"{base_url}/pocp/capabilities",
            invoke_url=f"{base_url}/pocp/invoke",
            proof_url=f"{base_url}/pocp/proofs",
            settlement_ack_url=f"{base_url}/pocp/settlements/ack",
        )
