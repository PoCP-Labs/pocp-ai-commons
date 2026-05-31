from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SettlementParticipant:
    entity_id: str
    role: str
    unit: str
    amount: float
    reason: str


@dataclass
class SettlementRecordDraft:
    task_id: str
    contribution_id: str | None = None
    participants: list[SettlementParticipant] = field(default_factory=list)
    status: str = "pending"
    treasury_fee: float = 0.0
    sponsor_pool_id: str | None = None


class SettlementPolicy:
    """Public reference settlement policy.

    Commercial settlement logic, private fee rules, and risk-based adjustments
    should live outside the public core.
    """

    def explain(self, settlement: SettlementRecordDraft) -> str:
        return (
            f"Settlement for task {settlement.task_id} includes "
            f"{len(settlement.participants)} participant reward records."
        )
