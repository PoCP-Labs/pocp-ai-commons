from __future__ import annotations
import uuid
from backend.services.cip.types import InvocationData

class CIPInvocationLedger:
    def __init__(self) -> None:
        self.invocations: dict[str, InvocationData] = {}

    def create(self, task_id: str, caller_entity_id: str, callee_entity_id: str, capability_id: str, input_hash: str, cost_unit: str | None = None, cost_amount: float = 0.0) -> InvocationData:
        invocation = InvocationData(
            invocation_id=f"invoke_{uuid.uuid4().hex[:16]}",
            task_id=task_id,
            caller_entity_id=caller_entity_id,
            callee_entity_id=callee_entity_id,
            capability_id=capability_id,
            input_hash=input_hash,
            cost_unit=cost_unit,
            cost_amount=cost_amount,
        )
        self.invocations[invocation.invocation_id] = invocation
        return invocation

    def complete(self, invocation_id: str, output_hash: str) -> InvocationData:
        invocation = self.invocations[invocation_id]
        invocation.output_hash = output_hash
        invocation.status = "completed"
        return invocation
