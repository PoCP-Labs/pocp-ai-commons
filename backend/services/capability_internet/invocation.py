from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import uuid

@dataclass
class Invocation:
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
    signature: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

class InvocationService:
    def create(self, task_id: str, caller_entity_id: str, callee_entity_id: str,
               capability_id: str, input_hash: str, cost_unit: str | None = None,
               cost_amount: float = 0.0) -> Invocation:
        return Invocation(f"invoke_{uuid.uuid4().hex[:16]}", task_id, caller_entity_id,
                          callee_entity_id, capability_id, input_hash,
                          cost_unit=cost_unit, cost_amount=cost_amount)

    def complete(self, invocation: Invocation, output_hash: str) -> Invocation:
        invocation.output_hash = output_hash
        invocation.status = "completed"
        return invocation
