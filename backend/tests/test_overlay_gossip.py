"""Tests for overlay peer gossip (v0.2b)."""

import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401
from database import Base
from models.protocol_overlay import ProtocolOverlayBatch, ProtocolOverlayEvent
from schemas.federation import TrustedNode
from services.network.gossip import (
    build_gossip_payload,
    push_gossip_to_trusted_peers,
    receive_gossip_payload,
)


class OverlayGossipTests(unittest.TestCase):
    def setUp(self):
        self._persist_prev = os.environ.get("POCP_OVERLAY_PERSIST")
        self._gossip_prev = os.environ.get("POCP_OVERLAY_GOSSIP")
        os.environ["POCP_OVERLAY_PERSIST"] = "true"
        os.environ["POCP_OVERLAY_GOSSIP"] = "true"
        self._trusted_backup = os.environ.get("POCP_TRUSTED_NODES")
        os.environ["POCP_TRUSTED_NODES"] = (
            '[{"node_id": "peer-a", "base_url": "http://peer-a:9000", "trust_weight": 0.9}]'
        )

        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        from services.network import persistence

        self._orig_session_fn = persistence._session
        persistence._session = self.Session

    def tearDown(self):
        from services.network import persistence

        persistence._session = self._orig_session_fn
        self._trusted_backup = getattr(self, "_trusted_backup", None)
        if self._persist_prev is None:
            os.environ.pop("POCP_OVERLAY_PERSIST", None)
        else:
            os.environ["POCP_OVERLAY_PERSIST"] = self._persist_prev
        if self._gossip_prev is None:
            os.environ.pop("POCP_OVERLAY_GOSSIP", None)
        else:
            os.environ["POCP_OVERLAY_GOSSIP"] = self._gossip_prev
        if self._trusted_backup is None:
            os.environ.pop("POCP_TRUSTED_NODES", None)
        else:
            os.environ["POCP_TRUSTED_NODES"] = self._trusted_backup

    def test_receive_gossip_imports_events(self):
        payload = build_gossip_payload(
            source_node_id="peer-a",
            events=[
                {
                    "schema": "pocp.protocol_event.v0.1",
                    "event_id": "evt_gossip_1",
                    "event_type": "FederatedProofOffered",
                    "node_id": "peer-a",
                    "payload": {"contribution_id": "c1"},
                    "payload_hash": "sha256:abc",
                    "event_hash": "sha256:def",
                    "timestamp": "2026-01-01T00:00:00Z",
                }
            ],
            batch={
                "batch_id": "batch_g1",
                "event_count": 1,
                "event_hashes": ["sha256:def"],
                "event_merkle_root": "sha256:root",
                "batch_hash": "sha256:batch",
            },
        )
        result = receive_gossip_payload(payload)
        self.assertEqual(result["imported"], 1)
        self.assertTrue(result["batch_imported"])

        db = self.Session()
        try:
            self.assertIsNotNone(db.get(ProtocolOverlayEvent, "evt_gossip_1"))
            self.assertIsNotNone(db.get(ProtocolOverlayBatch, "batch_g1"))
        finally:
            db.close()

    def test_receive_rejects_untrusted_source(self):
        payload = build_gossip_payload(source_node_id="evil-node", events=[])
        with self.assertRaises(ValueError):
            receive_gossip_payload(payload)

    @patch("services.network.gossip._post_json")
    @patch("services.network.gossip.load_trusted_nodes")
    def test_push_gossip_to_peers(self, mock_load, mock_post):
        mock_load.return_value = [
            TrustedNode(node_id="peer-a", base_url="http://peer-a:9000", trust_weight=0.9)
        ]
        mock_post.return_value = {"imported": 1, "skipped": 0}

        events = [
            {
                "schema": "pocp.protocol_event.v0.1",
                "event_id": "evt_push_1",
                "event_type": "InvocationCreated",
                "event_hash": "sha256:x",
            }
        ]
        result = push_gossip_to_trusted_peers(events=events, batch={"batch_id": "b1"})
        self.assertTrue(result["ran"])
        self.assertEqual(result["peers_ok"], 1)
        mock_post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
