from __future__ import annotations
from datetime import datetime, timezone
from backend.services.cip.types import NodeProfileData

class CIPHeartbeatService:
    def mark_active(self, node: NodeProfileData) -> NodeProfileData:
        node.status = "active"
        node.metadata["last_heartbeat_at"] = datetime.now(timezone.utc).isoformat()
        return node
