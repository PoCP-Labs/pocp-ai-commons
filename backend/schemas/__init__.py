from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EntityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_type: str
    name: str
    description: str | None = None
    owner_id: str | None = None
    creator_id: str | None = None
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_id: str
    version: str
    prompt_template: str | None = None
    maintainer_id: str | None = None


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_id: str
    config: dict[str, Any] = Field(default_factory=dict)
    maintainer_id: str | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str | None = None
    sponsor_id: str | None = None
    status: str
    created_at: datetime


class ParticipantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_id: str
    role: str
    weight: float
    evidence: dict[str, Any] = Field(default_factory=dict)


class AiVerifierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_provider: str
    score: float
    feedback: str | None = None
    passed: bool
    created_at: datetime


class HumanReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reviewer_id: str
    approved: bool
    feedback: str | None = None
    created_at: datetime


class ContributionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    primary_entity_id: str
    contribution_type: str
    description: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    status: str
    created_at: datetime
    participants: list[ParticipantOut] = Field(default_factory=list)
    ai_verifications: list[AiVerifierOut] = Field(default_factory=list)
    human_reviews: list[HumanReviewOut] = Field(default_factory=list)


class WalletOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_id: str
    cp_balance: float
    ai_credits: float


class ReputationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_id: str
    score: float
    category: str
    updated_at: datetime


class LedgerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contribution_id: str | None = None
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


# --- Input schemas ---


class EntityCreate(BaseModel):
    entity_type: str
    name: str
    description: str | None = None
    owner_id: str | None = None
    creator_id: str | None = None


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    sponsor_id: str | None = None


class ParticipantIn(BaseModel):
    entity_id: str
    role: str
    weight: float = 0.0
    evidence: dict[str, Any] = Field(default_factory=dict)


class ContributionCreate(BaseModel):
    task_id: str
    primary_entity_id: str
    contribution_type: str = "knowledge"
    description: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    participants: list[ParticipantIn] = Field(default_factory=list)


class AiVerifyIn(BaseModel):
    model_provider: str = "deepseek"
    score: float = 0.85
    feedback: str = "Content meets quality standards."


class ApproveIn(BaseModel):
    reviewer_id: str
    feedback: str = "Approved by human reviewer."


class GraphNode(BaseModel):
    id: str
    entity_type: str
    name: str
    reputation: float = 0.0
    cp_balance: float = 0.0
    ai_credits: float = 0.0


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str
    contribution_id: str | None = None
    weight: float = 0.0


class ContributionGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_id: str
    org_type: str
    governance_proxy_id: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class OrganizationCreate(BaseModel):
    name: str
    description: str | None = None
    org_type: str = "community"
    governance_proxy_id: str
    creator_id: str | None = None


class SkillCreate(BaseModel):
    name: str
    description: str | None = None
    prompt_template: str | None = None
    maintainer_id: str
    version: str = "1.0.0"


class InvocationStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    step_order: int
    source_entity_id: str
    target_entity_id: str
    action: str


class InvocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    initiator_id: str
    task_id: str | None = None
    contribution_id: str | None = None
    model_provider: str | None = None
    status: str
    created_at: datetime
    steps: list[InvocationStepOut] = Field(default_factory=list)


class InvocationCreate(BaseModel):
    initiator_id: str
    skill_entity_id: str
    agent_entity_id: str | None = None
    model_provider: str = "deepseek"
    task_id: str | None = None
    contribution_id: str | None = None


class ChatRequest(BaseModel):
    entity_id: str
    message: str
    model_provider: str = "deepseek"


class ChatResponse(BaseModel):
    reply: str
    credits_used: float
    credits_remaining: float
    transaction_id: str
