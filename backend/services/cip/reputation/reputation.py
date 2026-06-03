from __future__ import annotations

from services.cip.types import ReputationData


class CIPReputationService:
    """Contextual reputation skeleton."""

    def update_success(
        self,
        entity_id: str,
        scope: str,
        current: ReputationData | None = None,
    ) -> ReputationData:
        if current is None:
            current = ReputationData(entity_id=entity_id, scope=scope)

        current.success_count += 1
        total = current.success_count + current.failure_count + current.dispute_count
        current.score = current.success_count / total if total else 0.0
        return current
