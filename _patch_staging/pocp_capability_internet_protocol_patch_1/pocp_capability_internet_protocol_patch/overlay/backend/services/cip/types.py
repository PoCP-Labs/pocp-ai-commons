from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class NodeProfileData:
    node_id: str
    entity_id: str
    node_type: str
    public_key: str | None = None
    base_url: str | None = None
    p2p_address: str | None = None
    health_url: str | None = None
    protocol_version: str = "pocp-node-v0.1"
    status: str = "registered"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class CapabilityData:
    capability_id: str
    entity_id: str
    node_id: str | None
    capability_type: str
    name: str
    unit: str
    price: dict[str, float] = field(default_factory=dict)
    verification_method: str = "human_review"
    availability: str = "available"
    risk_level: str = "low"

@dataclass
class InvocationData:
    invocation_id: str
    task_id: str
    caller_entity_id: str
    callee_entity_id: str
    capability_id: str
    input_hash: str
    output_hash: str | None = None
    cost_unit: str | None = None
    cost_amount: float = 0.0
    status: str = "created"

@dataclass
class ProofData:
    proof_id: str
    entity_id: str
    proof_type: str
    node_id: str | None = None
    task_id: str | None = None
    invocation_id: str | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    evidence_ref: str | None = None
    signature: str | None = None

@dataclass
class VerificationData:
    verification_id: str
    proof_id: str
    verifier_entity_id: str
    verification_type: str = "ai_advisory"
    score: float | None = None
    decision: str = "pending"
    reason: str = ""
    status: str = "pending"

@dataclass
class SettlementParticipantData:
    entity_id: str
    role: str
    unit: str
    amount: float
    reason: str

@dataclass
class SettlementData:
    settlement_id: str
    task_id: str
    participants: list[SettlementParticipantData]
    invocation_id: str | None = None
    verification_id: str | None = None
    status: str = "pending"

@dataclass
class TokenAccountData:
    entity_id: str
    cp_balance: float = 0.0
    ai_credit_balance: float = 0.0
    compute_credit_balance: float = 0.0
    pocp_token_balance_internal: float = 0.0

@dataclass
class ReputationData:
    entity_id: str
    scope: str
    score: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    dispute_count: int = 0

@dataclass
class GraphEdgeData:
    source_id: str
    target_id: str
    edge_type: str

@dataclass
class ProtocolEventData:
    event_id: str
    event_type: str
    entity_id: str
    node_id: str | None
    payload_hash: str
    timestamp: str
    nonce: str
    signature: str | None = None
