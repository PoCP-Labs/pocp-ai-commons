from __future__ import annotations
import hashlib
from datetime import datetime, timezone

class SignatureService:
    """Reference helper. Integrate Ed25519 before production use."""
    def body_hash(self, body: str) -> str:
        return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()

    def timestamp_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def verify_placeholder(self, signature: str | None) -> bool:
        return bool(signature)
