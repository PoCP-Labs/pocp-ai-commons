from __future__ import annotations

import uuid

from services.cip.types import (
    SettlementData,
    SettlementParticipantData,
    VerificationData,
)


class CIPSettlementService:
    """Settlement skeleton."""

    def create_settlement(
        self,
        task_id: str,
        verification: VerificationData,
        participants: list[SettlementParticipantData],
        invocation_id: str | None = None,
    ) -> SettlementData:
        if verification.decision not in {"approved", "human_approved"}:
            raise ValueError("Settlement requires approved verification.")

        return SettlementData(
            settlement_id=f"settle_{uuid.uuid4().hex[:16]}",
            task_id=task_id,
            participants=participants,
            invocation_id=invocation_id,
            verification_id=verification.verification_id,
            status="settled",
        )
