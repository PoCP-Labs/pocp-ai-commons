from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ComputeNodeProfile:
    entity_id: str
    node_name: str
    region: str = "unknown"
    hardware: dict[str, Any] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)
    verification_methods: list[str] = field(default_factory=lambda: ["log"])
    availability: str = "available"


@dataclass
class ComputeUsageRecord:
    task_id: str
    compute_node_entity_id: str
    unit: str
    amount: float
    input_hash: str | None = None
    output_hash: str | None = None
    status: str = "completed"
    metadata: dict[str, Any] = field(default_factory=dict)
