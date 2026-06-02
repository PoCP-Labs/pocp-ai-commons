from __future__ import annotations
import uuid
from .merkle import MerkleService
from .types import EventBatch, ProtocolEvent

class EventBatchService:
    def __init__(self) -> None:
        self.merkle = MerkleService()

    def create_batch(self, events: list[ProtocolEvent],
                     previous_batch_hash: str | None = None,
                     created_by_node_id: str | None = None) -> EventBatch:
        event_hashes = [event.event_hash() for event in events]
        root = self.merkle.merkle_root(event_hashes)
        return EventBatch(
            batch_id=f"batch_{uuid.uuid4().hex[:16]}",
            event_hashes=event_hashes,
            event_merkle_root=root,
            previous_batch_hash=previous_batch_hash,
            created_by_node_id=created_by_node_id,
        )
