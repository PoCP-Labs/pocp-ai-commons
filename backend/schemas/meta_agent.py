"""Schemas for Meta Agent registry API."""

from typing import Any

from pydantic import BaseModel, Field


class MetaAgentCursorCapabilities(BaseModel):
    prompt_path: str | None = None
    prompt_available: bool = False
    prompt_chars: int = 0
    cursor_skill: str | None = None
    cursor_rule: str | None = None


class MetaAgentOut(BaseModel):
    entity_id: str
    name: str
    description: str | None = None
    status: str
    entity_type: str
    slug: str | None = None
    task_label: str | None = None
    roles: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    reports_to: str | None = None
    handoff_default: str | None = None
    orchestrates: list[str] = Field(default_factory=list)
    writable_paths: list[str] = Field(default_factory=list)
    prompt_path: str | None = None
    cursor_skill: str | None = None
    cursor_rule: str | None = None
    agent_config: dict[str, Any] = Field(default_factory=dict)
    cursor_capabilities: MetaAgentCursorCapabilities | None = None
    owner_id: str | None = None
    maintainer_id: str | None = None


class MetaAgentRosterEntry(BaseModel):
    entity_id: str
    name: str
    task_label: str
    reports_to: str | None = None


class MetaAgentRosterOut(BaseModel):
    layer: str
    count: int
    nexus_id: str
    agents: list[MetaAgentRosterEntry]
