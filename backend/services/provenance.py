"""OCTP-inspired provenance declarations for contribution evidence.

Inspired by Open Contribution Trust Protocol (OCTP): contributors declare how work
was created; the envelope travels with evidence and proof packets.
See docs/EXTERNAL-INTEGRATIONS.md
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from services.evidence import POCP_META_KEY
from services.federation_crypto import get_node_public_key_hex, sign_message

ProvenanceMode = Literal[
    "human_written",
    "ai_assisted",
    "ai_generated",
    "mixed",
    "unknown",
]

OCTP_ENVELOPE_VERSION = "octp-compatible-v0.1"


class ProvenanceDeclaration(BaseModel):
    """Machine-readable provenance envelope attached to contribution evidence."""

    creation_mode: ProvenanceMode = "unknown"
    ai_tools_used: list[str] = Field(default_factory=list)
    human_experts_cited: list[str] = Field(default_factory=list)
    declared_by_entity_id: str | None = None
    review_depth: str | None = None
    envelope_version: str = OCTP_ENVELOPE_VERSION
    notes: str | None = None
    verification_claims: list[dict[str, Any]] = Field(default_factory=list)


def build_provenance_envelope(
    *,
    declared_by_entity_id: str,
    creation_mode: ProvenanceMode = "unknown",
    ai_tools_used: list[str] | None = None,
    human_experts_cited: list[str] | None = None,
    review_depth: str | None = None,
    notes: str | None = None,
    verification_claims: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    declaration = ProvenanceDeclaration(
        creation_mode=creation_mode,
        ai_tools_used=ai_tools_used or [],
        human_experts_cited=human_experts_cited or [],
        declared_by_entity_id=declared_by_entity_id,
        review_depth=review_depth,
        notes=notes,
        verification_claims=verification_claims or [],
    )
    envelope = declaration.model_dump(exclude_none=True)
    if extra:
        envelope.update(extra)
    return envelope


def sign_provenance_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    """OCTP-style cryptographic binding of the provenance declaration."""
    payload = {k: v for k, v in envelope.items() if k != "integrity"}
    material = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    envelope_hash = hashlib.sha256(material.encode("utf-8")).hexdigest()
    public_key = get_node_public_key_hex()
    signature = sign_message(envelope_hash) if public_key else None
    signed = dict(envelope)
    signed["integrity"] = {
        "envelope_hash": envelope_hash,
        "hash_algorithm": "sha256",
        "signature": signature,
        "signer_public_key": public_key,
        "signed": signature is not None and public_key is not None,
    }
    return signed


def attach_provenance_to_evidence(
    evidence: dict,
    *,
    declared_by_entity_id: str,
    creation_mode: ProvenanceMode = "unknown",
    ai_tools_used: list[str] | None = None,
    human_experts_cited: list[str] | None = None,
    review_depth: str | None = None,
    notes: str | None = None,
    verification_claims: list[dict[str, Any]] | None = None,
) -> dict:
    """Attach OCTP-compatible provenance under evidence._pocp.provenance."""
    updated = dict(evidence)
    meta = dict(updated.get(POCP_META_KEY) or {})
    meta["provenance"] = sign_provenance_envelope(
        build_provenance_envelope(
            declared_by_entity_id=declared_by_entity_id,
            creation_mode=creation_mode,
            ai_tools_used=ai_tools_used,
            human_experts_cited=human_experts_cited,
            review_depth=review_depth,
            notes=notes,
            verification_claims=verification_claims,
        )
    )
    updated[POCP_META_KEY] = meta
    return updated


def provenance_from_evidence(evidence: dict | None) -> dict | None:
    if not evidence:
        return None
    meta = evidence.get(POCP_META_KEY) or {}
    return meta.get("provenance")
