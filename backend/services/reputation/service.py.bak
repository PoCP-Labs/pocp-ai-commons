from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import uuid

@dataclass
class ReputationRecord:
    reputation_id: str
    entity_id: str
    scope: str
    score: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    dispute_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

class ReputationService:
    def success(self, entity_id: str, scope: str,
                current: ReputationRecord | None = None) -> ReputationRecord:
        record = current or ReputationRecord(f"rep_{uuid.uuid4().hex[:16]}", entity_id, scope)
        record.success_count += 1
        total = record.success_count + record.failure_count + record.dispute_count
        record.score = record.success_count / total if total else 0.0
        return record
