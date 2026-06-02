"""Tests for ProtocolEvent overlay DB persistence (v0.2)."""

import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401
from database import Base
from models.protocol_overlay import OverlayEventMempoolStatus, ProtocolOverlayBatch, ProtocolOverlayEvent
from services.network.persistence import (
    count_batches_in_db,
    count_pending_in_db,
    list_events_from_db,
    overlay_persist_enabled,
)
from services.network.runtime import enqueue_event, overlay_status, reset_overlay_runtime, seal_batch
from services.network.types import ProtocolEvent


class OverlayPersistenceTests(unittest.TestCase):
    def setUp(self):
        self._persist_prev = os.environ.get("POCP_OVERLAY_PERSIST")
        os.environ["POCP_OVERLAY_PERSIST"] = "true"
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        from services.network import persistence

        self._orig_session_fn = persistence._session
        persistence._session = self.Session
        reset_overlay_runtime()

    def tearDown(self):
        reset_overlay_runtime()
        from services.network import persistence

        persistence._session = self._orig_session_fn
        if self._persist_prev is None:
            os.environ.pop("POCP_OVERLAY_PERSIST", None)
        else:
            os.environ["POCP_OVERLAY_PERSIST"] = self._persist_prev

    def test_persist_enabled(self):
        self.assertTrue(overlay_persist_enabled())

    def test_enqueue_persists_pending_row(self):
        event = ProtocolEvent.create("TestPersist", {"n": 1}, entity_id="e1", node_id="n1")
        enqueue_event(event)
        self.assertEqual(count_pending_in_db(), 1)
        rows = list_events_from_db(mempool_status="pending", limit=5)
        self.assertEqual(rows[0]["event_id"], event.event_id)

    def test_seal_batch_persists_batch_and_marks_sealed(self):
        event = ProtocolEvent.create("SealMe", {"x": 2}, entity_id="e1", node_id="n1")
        enqueue_event(event)
        sealed = seal_batch(created_by_node_id="n1")
        self.assertTrue(sealed["sealed"])
        self.assertEqual(count_pending_in_db(), 0)
        self.assertEqual(count_batches_in_db(), 1)

        db = self.Session()
        try:
            row = db.get(ProtocolOverlayEvent, event.event_id)
            self.assertEqual(row.mempool_status, OverlayEventMempoolStatus.sealed)
            self.assertIsNotNone(row.batch_id)
            batch = db.get(ProtocolOverlayBatch, row.batch_id)
            self.assertIsNotNone(batch)
            self.assertEqual(batch.event_count, 1)
        finally:
            db.close()

    def test_overlay_status_reports_persist(self):
        event = ProtocolEvent.create("StatusEvt", {}, node_id="n1")
        enqueue_event(event)
        status = overlay_status()
        self.assertTrue(status["persist_enabled"])
        self.assertEqual(status["transport"], "db_v0.2")


if __name__ == "__main__":
    unittest.main()
