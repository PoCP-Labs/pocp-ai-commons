from __future__ import annotations
from dataclasses import dataclass

@dataclass
class SybilRiskSignal:
    entity_id: str
    risk_level: str
    reason: str

class AntiSybilService:
    def evaluate_basic(self, entity_id: str, events_count: int, unique_counterparties: int) -> SybilRiskSignal:
        if events_count > 20 and unique_counterparties <= 1:
            return SybilRiskSignal(entity_id, "high", "Many events with too few counterparties.")
        if events_count > 10 and unique_counterparties <= 2:
            return SybilRiskSignal(entity_id, "medium", "Possible repeated interaction pattern.")
        return SybilRiskSignal(entity_id, "low", "No obvious basic Sybil signal.")
