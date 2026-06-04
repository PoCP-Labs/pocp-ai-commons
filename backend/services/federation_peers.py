"""HTTP client utilities for federated peer nodes."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from schemas.federation import TrustedNode
from services.trust_config import load_trusted_nodes

POCP_DIALOGUE_HMAC_VERSION = "pocp-dialogue-v1"
_DIALOGUE_HMAC_CLOCK_SKEW = int(os.getenv("POCP_PEER_DIALOGUE_HMAC_SKEW_SECONDS", "120"))
_DIALOGUE_SEEN_NONCES: dict[str, float] = {}


@dataclass(frozen=True)
class DialogueHmacResult:
    ok: bool
    node_id: str | None = None
    reason: str | None = None


def peer_dialogue_hmac_secret() -> str | None:
    secret = os.getenv("POCP_PEER_DIALOGUE_HMAC", "").strip()
    return secret or None


def peer_dialogue_hmac_required() -> bool:
    return os.getenv("POCP_PEER_DIALOGUE_HMAC_REQUIRED", "false").lower() in (
        "true",
        "1",
        "yes",
        "on",
    )


def peer_dialogue_hmac_enabled() -> bool:
    return peer_dialogue_hmac_secret() is not None


def dialogue_body_digest(body: dict[str, Any]) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def dialogue_hmac_message(*, node_id: str, nonce: str, timestamp: int, body_digest: str) -> str:
    return f"{POCP_DIALOGUE_HMAC_VERSION}|{node_id}|{nonce}|{timestamp}|{body_digest}"


def _dialogue_header(headers: dict[str, str], name: str) -> str | None:
    lower = name.lower()
    for key, value in headers.items():
        if key.lower() == lower:
            return str(value).strip()
    return None


def _prune_dialogue_nonce_cache(*, now: float, ttl: float) -> None:
    expired = [key for key, expires in _DIALOGUE_SEEN_NONCES.items() if expires <= now]
    for key in expired:
        _DIALOGUE_SEEN_NONCES.pop(key, None)


def _register_dialogue_nonce(node_id: str, nonce: str, *, ttl_seconds: int) -> bool:
    now = time.time()
    _prune_dialogue_nonce_cache(now=now, ttl=ttl_seconds)
    key = f"{node_id}:{nonce}"
    if key in _DIALOGUE_SEEN_NONCES and _DIALOGUE_SEEN_NONCES[key] > now:
        return False
    _DIALOGUE_SEEN_NONCES[key] = now + ttl_seconds
    return True


def build_dialogue_hmac_headers(body: dict[str, Any], *, source_node_id: str) -> dict[str, str]:
    """Attach optional HMAC headers for POST /api/v1/federation/dialogue (CIP-P3.3)."""
    secret = peer_dialogue_hmac_secret()
    if not secret:
        return {}
    node_id = source_node_id
    nonce = str(uuid.uuid4())
    timestamp = int(time.time())
    digest = dialogue_body_digest(body)
    message = dialogue_hmac_message(node_id=node_id, nonce=nonce, timestamp=timestamp, body_digest=digest)
    signature = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "X-POCP-Dialogue-Node-Id": node_id,
        "X-POCP-Dialogue-Nonce": nonce,
        "X-POCP-Dialogue-Timestamp": str(timestamp),
        "X-POCP-Dialogue-Body-Digest": digest,
        "X-POCP-Dialogue-Signature-Alg": "hmac-sha256",
        "X-POCP-Dialogue-Signature": signature,
    }


def verify_incoming_dialogue_hmac(
    body: dict[str, Any],
    headers: dict[str, str],
) -> DialogueHmacResult:
    """
    Verify federation dialogue POST when POCP_PEER_DIALOGUE_HMAC is configured.
    Backward compatible: when secret unset, always ok; when set but not required,
    unsigned requests are accepted unless signature is present (then validated).
    """
    secret = peer_dialogue_hmac_secret()
    if not secret:
        return DialogueHmacResult(ok=True)

    node_id = _dialogue_header(headers, "X-POCP-Dialogue-Node-Id")
    nonce = _dialogue_header(headers, "X-POCP-Dialogue-Nonce")
    timestamp_raw = _dialogue_header(headers, "X-POCP-Dialogue-Timestamp")
    signature = _dialogue_header(headers, "X-POCP-Dialogue-Signature")
    algorithm = (_dialogue_header(headers, "X-POCP-Dialogue-Signature-Alg") or "hmac-sha256").lower()

    if not node_id or not nonce or not timestamp_raw or not signature:
        if peer_dialogue_hmac_required():
            return DialogueHmacResult(ok=False, reason="missing_dialogue_hmac_headers")
        return DialogueHmacResult(ok=True)

    if algorithm not in ("hmac-sha256", "hmac_sha256", "hmac"):
        return DialogueHmacResult(ok=False, node_id=node_id, reason=f"unsupported_algorithm:{algorithm}")

    try:
        timestamp = int(timestamp_raw)
    except ValueError:
        return DialogueHmacResult(ok=False, node_id=node_id, reason="invalid_timestamp")

    now = int(time.time())
    if abs(now - timestamp) > _DIALOGUE_HMAC_CLOCK_SKEW:
        return DialogueHmacResult(ok=False, node_id=node_id, reason="timestamp_out_of_range")

    if not _register_dialogue_nonce(node_id, nonce, ttl_seconds=_DIALOGUE_HMAC_CLOCK_SKEW * 2):
        return DialogueHmacResult(ok=False, node_id=node_id, reason="nonce_replay")

    expected_digest = dialogue_body_digest(body)
    header_digest = _dialogue_header(headers, "X-POCP-Dialogue-Body-Digest")
    if header_digest and header_digest.lower() != expected_digest.lower():
        return DialogueHmacResult(ok=False, node_id=node_id, reason="body_digest_mismatch")

    message = dialogue_hmac_message(
        node_id=node_id,
        nonce=nonce,
        timestamp=timestamp,
        body_digest=expected_digest,
    )
    expected_sig = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, signature.lower()):
        return DialogueHmacResult(ok=False, node_id=node_id, reason="invalid_signature")

    from_ref = body.get("from") if isinstance(body.get("from"), dict) else {}
    refs = body.get("refs") if isinstance(body.get("refs"), dict) else {}
    claimed = from_ref.get("node_id") or refs.get("routed_from_node_id")
    if claimed and str(claimed) != node_id:
        return DialogueHmacResult(ok=False, node_id=node_id, reason="node_id_mismatch")

    if peer_dialogue_hmac_required() or os.getenv("POCP_PEER_DIALOGUE_HMAC_TRUSTED_ONLY", "false").lower() in (
        "true",
        "1",
        "yes",
        "on",
    ):
        from services.trust_config import trusted_nodes_map

        if node_id not in trusted_nodes_map():
            return DialogueHmacResult(ok=False, node_id=node_id, reason="untrusted_node_id")

    return DialogueHmacResult(ok=True, node_id=node_id)


def clear_dialogue_hmac_cache() -> None:
    _DIALOGUE_SEEN_NONCES.clear()


def _local_node_id_for_dialogue() -> str:
    try:
        from services.compute_registry import compute_status_manifest

        return str(compute_status_manifest().get("node_id") or os.getenv("POCP_NODE_ID") or "unknown")
    except Exception:
        return os.getenv("POCP_NODE_ID", "unknown")


def _get_json(url: str, timeout: float = 20.0) -> dict | list:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode())


def _post_json(url: str, body: dict, timeout: float = 30.0, extra_headers: dict[str, str] | None = None) -> dict:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if "/federation/dialogue" in url:
        headers.update(build_dialogue_hmac_headers(body, source_node_id=_local_node_id_for_dialogue()))
    if extra_headers:
        headers.update(extra_headers)
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def probe_peer(base_url: str) -> dict:
    root = base_url.rstrip("/")
    result: dict = {"base_url": root, "reachable": False}
    try:
        health = _get_json(f"{root}/health")
        node = _get_json(f"{root}/api/v1/federation/node")
        ledger_verify = _get_json(f"{root}/api/v1/ledger/verify")
        anchor = _get_json(f"{root}/api/v1/ledger/anchor?skip_cosign=true")
        result.update(
            {
                "reachable": True,
                "health": health,
                "node": node,
                "ledger_valid": ledger_verify.get("valid"),
                "ledger_count": ledger_verify.get("count"),
                "anchor_merkle_root": anchor.get("merkle_root"),
                "anchor_tip_hash": anchor.get("tip_hash"),
            }
        )
    except urllib.error.HTTPError as exc:
        result["error"] = f"HTTP {exc.code}: {exc.read().decode()}"
    except urllib.error.URLError as exc:
        result["error"] = str(exc.reason)
    except Exception as exc:
        result["error"] = str(exc)
    return result


def verify_remote_ledger(base_url: str, expected_tip_hash: str | None = None) -> None:
    """Raise ValueError if remote ledger is invalid or tip hash mismatches."""
    root = base_url.rstrip("/")
    verify = _get_json(f"{root}/api/v1/ledger/verify")
    if not verify.get("valid"):
        raise ValueError(f"Remote ledger invalid at {root}")

    if not expected_tip_hash:
        return

    anchor = _get_json(f"{root}/api/v1/ledger/anchor?skip_cosign=true")
    tip = anchor.get("tip_hash")
    if tip and tip != expected_tip_hash:
        raise ValueError("Remote ledger tip_hash does not match proof ledger_tip_hash")


def verify_remote_ledger_record(base_url: str, record_hash: str | None) -> None:
    """Ensure remote ledger chain is valid and contains the signed approval record."""
    if not record_hash:
        raise ValueError("Proof missing ledger record hash for verification")
    root = base_url.rstrip("/")
    verify = _get_json(f"{root}/api/v1/ledger/verify")
    if not verify.get("valid"):
        raise ValueError(f"Remote ledger invalid at {root}")
    export = _get_json(f"{root}/api/v1/ledger/export")
    known = {row.get("record_hash") for row in export.get("records", []) if row.get("record_hash")}
    if record_hash not in known:
        raise ValueError(f"Remote ledger missing approval record_hash {record_hash[:16]}…")


def fetch_proof(base_url: str, contribution_id: str) -> dict:
    return _get_json(f"{base_url.rstrip('/')}/api/v1/contributions/{contribution_id}/proof")


def fetch_federation_intelligence(base_url: str, contribution_id: str) -> dict | None:
    """Fetch intelligence + proof bundle from a peer (optional during sync)."""
    root = base_url.rstrip("/")
    try:
        return _get_json(f"{root}/api/v1/intelligence/federation/export/{contribution_id}")
    except Exception:
        return None


def post_import_proof(target_base_url: str, source_node_id: str, proof: dict) -> dict:
    return _post_json(
        f"{target_base_url.rstrip('/')}/api/v1/federation/import-proof",
        {"source_node_id": source_node_id, "proof": proof},
    )
