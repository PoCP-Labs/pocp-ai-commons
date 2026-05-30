"""OCTP-inspired provenance declarations for contribution evidence.

Inspired by Open Contribution Trust Protocol (OCTP): contributors declare how work
was created; the envelope travels with evidence and proof packets.
See docs/EXTERNAL-INTEGRATIONS.md
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from services.evidence import POCP_META_KEY

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


def build_provenance_envelope(
    *,
    declared_by_entity_id: str,
    creation_mode: ProvenanceMode = "unknown",
    ai_tools_used: list[str] | None = None,
    human_experts_cited: list[str] | None = None,
    review_depth: str | None = None,
    notes: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    declaration = ProvenanceDeclaration(
        creation_mode=creation_mode,
        ai_tools_used=ai_tools_used or [],
        human_experts_cited=human_experts_cited or [],
        declared_by_entity_id=declared_by_entity_id,
        review_depth=review_depth,
        notes=notes,
    )
    envelope = declaration.model_dump(exclude_none=True)
    if extra:
        envelope.update(extra)
    return envelope


def attach_provenance_to_evidence(
    evidence: dict,
    *,
    declared_by_entity_id: str,
    creation_mode: ProvenanceMode = "unknown",
    ai_tools_used: list[str] | None = None,
    human_experts_cited: list[str] | None = None,
    review_depth: str | None = None,
    notes: str | None = None,
) -> dict:
    """Attach OCTP-compatible provenance under evidence._pocp.provenance."""
    updated = dict(evidence)
    meta = dict(updated.get(POCP_META_KEY) or {})
    meta["provenance"] = build_provenance_envelope(
        declared_by_entity_id=declared_by_entity_id,
        creation_mode=creation_mode,
        ai_tools_used=ai_tools_used,
        human_experts_cited=human_experts_cited,
        review_depth=review_depth,
        notes=notes,
    )
    updated[POCP_META_KEY] = meta
    return updated


def provenance_from_evidence(evidence: dict | None) -> dict | None:
    if not evidence:
        return None
    meta = evidence.get(POCP_META_KEY) or {}
    return meta.get("provenance")
