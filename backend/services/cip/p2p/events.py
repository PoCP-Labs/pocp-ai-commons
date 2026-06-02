from __future__ import annotations
from services.cip.types import ProtocolEventData

class CIPEventLog:
    def __init__(self) -> None:
        self.events: list[ProtocolEventData] = []

    def append(self, event: ProtocolEventData) -> ProtocolEventData:
        self.events.append(event)
        return event

    def by_entity(self, entity_id: str) -> list[ProtocolEventData]:
        return [e for e in self.events if e.entity_id == entity_id]
