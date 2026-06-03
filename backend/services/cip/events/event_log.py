from __future__ import annotations

import uuid

from services.cip.types import ProtocolEventData


class CIPEventLog:
    """Append-only in-memory event log."""

    def __init__(self) -> None:
        self.events: list[ProtocolEventData] = []

    def append(
        self,
        event_type: str,
        entity_id: str,
        payload_ref: str,
        node_id: str | None = None,
        signature: str | None = None,
    ) -> ProtocolEventData:
        event = ProtocolEventData(
            event_id=f"evt_{uuid.uuid4().hex[:16]}",
            event_type=event_type,
            entity_id=entity_id,
            node_id=node_id,
            payload_ref=payload_ref,
            signature=signature,
        )
        self.events.append(event)
        return event
