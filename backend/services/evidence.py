"""Content-addressed evidence hashing for portable contribution verification."""

import hashlib
import json

POCP_SPEC_VERSION = "0.1"
POCP_META_KEY = "_pocp"


def canonicalize_evidence(evidence: dict) -> str:
    """Stable JSON for hashing (excludes prior _pocp metadata)."""
    clean = {k: v for k, v in evidence.items() if k != POCP_META_KEY}
    return json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash_evidence(evidence: dict) -> str:
    return hashlib.sha256(canonicalize_evidence(evidence).encode("utf-8")).hexdigest()


def enrich_evidence(evidence: dict | None) -> dict:
    base = dict(evidence or {})
    base.pop(POCP_META_KEY, None)
    content_hash = hash_evidence(base)
    base[POCP_META_KEY] = {
        "content_hash": content_hash,
        "spec_version": POCP_SPEC_VERSION,
    }
    return base
