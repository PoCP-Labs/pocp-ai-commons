from __future__ import annotations
from .types import ConfirmationStatus, ProtocolEvent

class ConfirmationService:
    LEVELS = {
        0: "event_submitted",
        1: "accepted_by_mempool",
        2: "proof_verified",
        3: "settlement_proposed",
        4: "challenge_window_passed",
        5: "settlement_finalized",
    }

    def status_for_event(self, event: ProtocolEvent, level: int) -> ConfirmationStatus:
        label = self.LEVELS.get(level, "unknown")
        return ConfirmationStatus(event_id=event.event_id, level=level, label=label, finalized=level >= 5)
