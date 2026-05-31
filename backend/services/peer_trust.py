"""AGT-inspired peer trust handshake — HMAC + Ed25519 over trusted node keys (BI-2)."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

from services.federation_crypto import get_node_public_key_hex, sign_message, verify_message
from services.trust_config import trusted_nodes_map

POCP_PEER_HANDSHAKE_VERSION = "pocp-peer-v1"
DEFAULT_TTL_SECONDS = int(os.getenv("POCP_PEER_HANDSHAKE_TTL_SECONDS", "300"))
DEFAULT_CLOCK_SKEW_SECONDS = int(os.getenv("POCP_PEER_CLOCK_SKEW_SECONDS", "120"))

_issued_challenges: dict[str, float] = {}
_seen_nonces: dict[str, float] = {}


@dataclass(frozen=True)
class PeerAuthResult:
    ok: bool
    node_id: str | None = None
    algorithm: str | None = None
    reason: str | None = None


def local_node_id() -> str:
    from services.compute_registry import compute_status_manifest

    return str(compute_status_manifest().get("node_id") or os.getenv("POCP_NODE_ID") or "local")


def peer_handshake_secret() -> str | None:
    secret = os.getenv("POCP_PEER_COMPUTE_SECRET", "").strip()
    return secret or None


def handshake_message(*, node_id: str, nonce: str, timestamp: int) -> str:
    return f"{POCP_PEER_HANDSHAKE_VERSION}|{node_id}|{nonce}|{timestamp}"


def _prune_cache(store: dict[str, float], *, now: float, ttl: float) -> None:
    expired = [key for key, expires in store.items() if expires <= now]
    for key in expired:
        store.pop(key, None)


def issue_peer_challenge(*, node_id: str | None = None, ttl_seconds: int | None = None) -> dict[str, Any]:
    """Server-issued nonce — optional challenge/response mode (AGT-style)."""
    ttl = ttl_seconds or DEFAULT_TTL_SECONDS
    peer_id = node_id or local_node_id()
    nonce = str(uuid.uuid4())
    expires_at = time.time() + ttl
    _issued_challenges[f"{peer_id}:{nonce}"] = expires_at
    _prune_cache(_issued_challenges, now=time.time(), ttl=ttl)
    return {
        "spec_version": "0.1",
        "handshake_version": POCP_PEER_HANDSHAKE_VERSION,
        "node_id": peer_id,
        "nonce": nonce,
        "expires_at": expires_at,
        "algorithms": peer_trust_algorithms(),
        "message_format": "pocp-peer-v1|{node_id}|{nonce}|{timestamp}",
    }


def peer_trust_algorithms() -> list[str]:
    algs = []
    if peer_handshake_secret():
        algs.append("hmac-sha256")
    if get_node_public_key_hex():
        algs.append("ed25519")
    return algs or ["hmac-sha256"]


def _register_seen_nonce(node_id: str, nonce: str, *, ttl_seconds: int) -> bool:
    """Return False if nonce was already used (replay)."""
    now = time.time()
    _prune_cache(_seen_nonces, now=now, ttl=ttl_seconds)
    key = f"{node_id}:{nonce}"
    if key in _seen_nonces and _seen_nonces[key] > now:
        return False
    _seen_nonces[key] = now + ttl_seconds
    return True


def _consume_issued_challenge(node_id: str, nonce: str) -> bool:
    key = f"{node_id}:{nonce}"
    expires = _issued_challenges.pop(key, None)
    if expires is None:
        return False
    return expires >= time.time()


def _header(headers: dict[str, str], name: str) -> str | None:
    lower = name.lower()
    for key, value in headers.items():
        if key.lower() == lower:
            return str(value).strip()
    return None


def _verify_hmac(message: str, signature_hex: str) -> bool:
    secret = peer_handshake_secret()
    if not secret:
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_hex.lower())


def verify_peer_handshake(headers: dict[str, str]) -> PeerAuthResult:
    node_id = _header(headers, "X-POCP-Peer-Node-Id")
    nonce = _header(headers, "X-POCP-Peer-Nonce")
    timestamp_raw = _header(headers, "X-POCP-Peer-Timestamp")
    signature = _header(headers, "X-POCP-Peer-Signature")
    algorithm = (_header(headers, "X-POCP-Peer-Signature-Alg") or "hmac-sha256").lower()

    if not node_id or not nonce or not timestamp_raw or not signature:
        return PeerAuthResult(ok=False, reason="missing_handshake_headers")

    try:
        timestamp = int(timestamp_raw)
    except ValueError:
        return PeerAuthResult(ok=False, reason="invalid_timestamp")

    now = int(time.time())
    if abs(now - timestamp) > DEFAULT_CLOCK_SKEW_SECONDS:
        return PeerAuthResult(ok=False, node_id=node_id, reason="timestamp_out_of_range")

    message = handshake_message(node_id=node_id, nonce=nonce, timestamp=timestamp)

    challenge_mode = os.getenv("POCP_PEER_HANDSHAKE_MODE", "shared_secret").lower()
    if challenge_mode == "challenge":
        if not _consume_issued_challenge(node_id, nonce):
            return PeerAuthResult(ok=False, node_id=node_id, reason="invalid_or_expired_challenge")
    elif not _register_seen_nonce(node_id, nonce, ttl_seconds=DEFAULT_TTL_SECONDS):
        return PeerAuthResult(ok=False, node_id=node_id, reason="nonce_replay")

    if algorithm == "ed25519":
        trusted = trusted_nodes_map().get(node_id)
        public_key = trusted.public_key if trusted and trusted.public_key else None
        if not public_key:
            return PeerAuthResult(ok=False, node_id=node_id, algorithm=algorithm, reason="unknown_peer_key")
        if not verify_message(message, signature, public_key):
            return PeerAuthResult(ok=False, node_id=node_id, algorithm=algorithm, reason="invalid_signature")
        return PeerAuthResult(ok=True, node_id=node_id, algorithm=algorithm)

    if algorithm not in ("hmac-sha256", "hmac_sha256", "hmac"):
        return PeerAuthResult(ok=False, node_id=node_id, reason=f"unsupported_algorithm:{algorithm}")

    if not _verify_hmac(message, signature):
        return PeerAuthResult(ok=False, node_id=node_id, algorithm="hmac-sha256", reason="invalid_signature")

    if node_id not in trusted_nodes_map() and os.getenv("POCP_PEER_REQUIRE_TRUSTED_NODE", "false").lower() in (
        "true",
        "1",
        "yes",
        "on",
    ):
        return PeerAuthResult(ok=False, node_id=node_id, algorithm="hmac-sha256", reason="untrusted_node_id")

    return PeerAuthResult(ok=True, node_id=node_id, algorithm="hmac-sha256")


def build_peer_auth_headers(
    *,
    source_node_id: str | None = None,
    nonce: str | None = None,
    prefer_ed25519: bool | None = None,
) -> dict[str, str]:
    """Attach handshake headers for outbound peer witness / inference / MCP calls."""
    node_id = source_node_id or local_node_id()
    nonce = nonce or str(uuid.uuid4())
    timestamp = int(time.time())
    message = handshake_message(node_id=node_id, nonce=nonce, timestamp=timestamp)
    headers = {
        "X-POCP-Peer-Node-Id": node_id,
        "X-POCP-Peer-Nonce": nonce,
        "X-POCP-Peer-Timestamp": str(timestamp),
    }

    use_ed25519 = prefer_ed25519
    if use_ed25519 is None:
        use_ed25519 = os.getenv("POCP_PEER_PREFER_ED25519", "false").lower() in ("true", "1", "yes", "on")

    if use_ed25519:
        signature = sign_message(message)
        if signature:
            headers["X-POCP-Peer-Signature-Alg"] = "ed25519"
            headers["X-POCP-Peer-Signature"] = signature
            return headers

    secret = peer_handshake_secret()
    if secret:
        digest = hmac.new(
            secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers["X-POCP-Peer-Signature-Alg"] = "hmac-sha256"
        headers["X-POCP-Peer-Signature"] = digest
        headers["X-POCP-Peer-Secret"] = secret
    return headers


def peer_trust_manifest() -> dict[str, Any]:
    from services.compute_registry import compute_status_manifest
    from services.finalization import is_auto_finalization_enabled
    from services.peer_compute import peer_compute_enabled, peer_witness_allowed

    manifest = compute_status_manifest()
    return {
        "spec_version": "0.1",
        "handshake_version": POCP_PEER_HANDSHAKE_VERSION,
        "node_id": manifest.get("node_id"),
        "public_key": get_node_public_key_hex(),
        "algorithms": peer_trust_algorithms(),
        "peer_compute_enabled": peer_compute_enabled(),
        "dev_bypass_enabled": peer_witness_allowed(),
        "shared_secret_configured": bool(peer_handshake_secret()),
        "trusted_peer_count": len(trusted_nodes_map()),
        "handshake_mode": os.getenv("POCP_PEER_HANDSHAKE_MODE", "shared_secret"),
        "ttl_seconds": DEFAULT_TTL_SECONDS,
        "clock_skew_seconds": DEFAULT_CLOCK_SKEW_SECONDS,
        "challenge_endpoint": "/api/v1/intelligence/compute/peer/challenge",
        "required_headers": [
            "X-POCP-Peer-Node-Id",
            "X-POCP-Peer-Nonce",
            "X-POCP-Peer-Timestamp",
            "X-POCP-Peer-Signature",
            "X-POCP-Peer-Signature-Alg",
        ],
        "legacy_header": "X-POCP-Peer-Secret",
        "auto_finalization_enabled": is_auto_finalization_enabled(),
        "finalization_mode": "entity_equal_policy_delegate",
    }


def clear_peer_trust_cache() -> None:
    _issued_challenges.clear()
    _seen_nonces.clear()
