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


class FederationSettlementIntentIn(BaseModel):
    spec_version: str = "pocp.federation_settlement.v0.4"
    consumer_node_id: str
    provider_node_id: str
    consumer_entity_id: str
    provider_entity_id: str | None = None
    receipt_hash: str
    receipt: dict[str, Any] = Field(default_factory=dict)
    consumer_tokens: float = 0.0
    provider_tokens: float = 0.0
    capability: str | None = None
    contribution_id: str | None = None
    job_id: str | None = None
    message: str | None = None
    signature: str | None = None
