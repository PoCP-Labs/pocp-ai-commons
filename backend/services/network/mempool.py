from __future__ import annotations
from collections import defaultdict
from .types import ProtocolEvent

class PoCPMempool:
    def __init__(self) -> None:
        self._pools: dict[str, list[ProtocolEvent]] = defaultdict(list)

    def add(self, event: ProtocolEvent) -> None:
        self._pools[event.event_type].append(event)

    def pending(self, event_type: str | None = None) -> list[ProtocolEvent]:
        if event_type:
            return list(self._pools.get(event_type, []))
        out: list[ProtocolEvent] = []
        for events in self._pools.values():
            out.extend(events)
        return out

    def drain(self, limit: int | None = None) -> list[ProtocolEvent]:
        events = self.pending()
        if limit is not None:
            events = events[:limit]
        drained_ids = {event.event_id for event in events}
        for key in list(self._pools.keys()):
            self._pools[key] = [e for e in self._pools[key] if e.event_id not in drained_ids]
        return events
