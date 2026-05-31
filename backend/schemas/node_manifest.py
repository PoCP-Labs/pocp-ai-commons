"""Node manifest schemas — capability-first."""

from typing import Any

from pydantic import BaseModel, Field


class NodeManifestCapabilityOut(BaseModel):
    capability_id: str | None = None
    capability_type: str
    name: str
    unit: str
    exchange_kind: str
    base_price: float | None = None
    price_model: str | None = None
    availability: str | None = None
    accepted_units: list[str] = Field(default_factory=list)
    source: str | None = None


class EntityNodeManifestOut(BaseModel):
    protocol: str
    kind: str = "entity"
    entity_id: str
    entity_type: str
    display_name: str
    description: str | None = None
    status: str
    facets: list[str] = Field(default_factory=list)
    capabilities: list[NodeManifestCapabilityOut | dict[str, Any]] = Field(default_factory=list)
    endpoints: dict[str, str] = Field(default_factory=dict)
    wallet_id: str | None = None
    portable_id: str | None = None
    roles: list[str] | None = None
    witness: dict[str, Any] | None = None
    compute_profile: dict[str, Any] | None = None
    updated_at: str


class InstanceNodeManifestOut(BaseModel):
    protocol: str
    kind: str = "instance"
    instance_id: str
    display_name: str
    facets: list[str] = Field(default_factory=list)
    archive_entity_id: str
    endpoints: dict[str, str] = Field(default_factory=dict)
    updated_at: str


class ProviderDirectoryItemOut(BaseModel):
    provider_entity_id: str
    provider_name: str
    provider_entity_type: str
    capability_id: str | None = None
    capability_type: str
    name: str
    unit: str
    exchange_kind: str
    base_price: float | None = None
    price_model: str | None = None
    availability: str | None = None
    source: str
    manifest_url: str


class ProviderDirectoryOut(BaseModel):
    spec_version: str
    count: int
    items: list[ProviderDirectoryItemOut] = Field(default_factory=list)
