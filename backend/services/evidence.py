"""Content-addressed evidence hashing for portable contribution verification."""

import hashlib
import json
from typing import Any

POCP_SPEC_VERSION = "0.1"
POCP_EVIDENCE_STANDARD_VERSION = "0.1"
POCP_META_KEY = "_pocp"

EVIDENCE_TYPE_ALIASES = {
    "artifact": "artifact",
    "artifacts": "artifact",
    "commit": "commit",
    "commits": "commit",
    "content": "content_preview",
    "content_preview": "content_preview",
    "diff": "diff",
    "patch": "diff",
    "link": "url",
    "links": "url",
    "note": "note",
    "notes": "note",
    "pull_request": "pull_request",
    "pr": "pull_request",
    "screenshot": "screenshot",
    "screenshots": "screenshot",
    "source": "url",
    "url": "url",
    "urls": "url",
}

STANDARD_EVIDENCE_TYPES = tuple(sorted(set(EVIDENCE_TYPE_ALIASES.values()) | {"other"}))


def canonicalize_evidence(evidence: dict) -> str:
    """Stable JSON for hashing (excludes prior _pocp metadata)."""
    clean = {k: v for k, v in evidence.items() if k != POCP_META_KEY}
    return json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash_evidence(evidence: dict) -> str:
    return hashlib.sha256(canonicalize_evidence(evidence).encode("utf-8")).hexdigest()


def evidence_type_for_key(key: str) -> str:
    normalized = key.lower().strip().replace("-", "_")
    return EVIDENCE_TYPE_ALIASES.get(normalized, "other")


def _compact_value(value: Any) -> Any:
    if isinstance(value, list):
        return [item for item in value if item not in (None, "")]
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items() if v not in (None, "")}
    return value


def standardize_evidence_items(evidence: dict | None) -> list[dict]:
    """Return evidence as typed, JSON-compatible review items."""
    items: list[dict] = []
    for key, value in (evidence or {}).items():
        if key == POCP_META_KEY:
            continue
        compact = _compact_value(value)
        if compact in (None, "", [], {}):
            continue
        evidence_type = evidence_type_for_key(key)
        items.append(
            {
                "type": evidence_type,
                "key": key,
                "label": key.replace("_", " ").strip().title(),
                "value": compact,
            }
        )
    return items


def evidence_types(evidence: dict | None) -> list[str]:
    return sorted({item["type"] for item in standardize_evidence_items(evidence)})


def enrich_evidence(evidence: dict | None) -> dict:
    base = dict(evidence or {})
    base.pop(POCP_META_KEY, None)
    content_hash = hash_evidence(base)
    base[POCP_META_KEY] = {
        "content_hash": content_hash,
        "evidence_standard": POCP_EVIDENCE_STANDARD_VERSION,
        "evidence_types": evidence_types(base),
        "spec_version": POCP_SPEC_VERSION,
    }
    return base
