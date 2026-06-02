from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class RoutingRequest:
    task_id: str
    task_type: str
    description: str
    budget: dict[str, float] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingStep:
    step: int
    entity_type: str
    capability_type: str
    entity_id: str | None = None
    capability_id: str | None = None
    reason: str = ""


@dataclass
class ExecutionPlan:
    task_id: str
    steps: list[RoutingStep]
    estimated_cost: dict[str, float] = field(default_factory=dict)
    risk_level: str = "unknown"
    explanation: str = ""


class NeuralRouter(Protocol):
    def route(self, request: RoutingRequest) -> ExecutionPlan:
        """Return an execution plan for a task."""
        ...
