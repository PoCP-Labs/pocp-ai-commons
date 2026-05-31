from typing import Any

from pydantic import BaseModel, Field


class FederationNodeOut(BaseModel):
    node_id: str
    spec_version: str
    public_key: str | None = None
    pqc_public_key: str | None = None
    crypto_suite: str | None = None
    node_mode: str = "full"
    public_endpoints: list[str] = Field(default_factory=list)


class TrustedNode(BaseModel):
    node_id: str
    base_url: str
    public_key: str | None = None
    pqc_public_key: str | None = None
    trust_weight: float = 0.5


class TrustListOut(BaseModel):
    trusted_nodes: list[TrustedNode] = Field(default_factory=list)
    source: str = "none"
    trust_list_hash: str | None = None


class ImportParticipant(BaseModel):
    entity_portable_id: str
    role: str
    weight: float = 0.0


class ImportEventPayload(BaseModel):
    source_node_id: str
    contribution_id: str
    task_title: str
    primary_entity_portable_id: str
    contribution_type: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    participants: list[ImportParticipant] = Field(default_factory=list)
    ledger_record_hash: str
    signature: str | None = None
