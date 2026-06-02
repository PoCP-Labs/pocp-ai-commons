from __future__ import annotations
import hashlib, uuid
from datetime import datetime, timezone
from backend.services.cip.types import ProtocolEventData

class CIPSignatureService:
    def hash_payload(self, payload: str) -> str:
        return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def create_event(self, event_type: str, entity_id: str, payload: str, node_id: str | None = None, signature: str | None = None) -> ProtocolEventData:
        return ProtocolEventData(
            event_id=f"evt_{uuid.uuid4().hex[:16]}",
            event_type=event_type,
            entity_id=entity_id,
            node_id=node_id,
            payload_hash=self.hash_payload(payload),
            timestamp=datetime.now(timezone.utc).isoformat(),
            nonce=f"nonce_{uuid.uuid4().hex[:16]}",
            signature=signature,
        )
