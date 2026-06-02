"""Tests for PN-4 federation overlay relay."""

import asyncio
import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from services.entity_dialogue import ENTITY_DIALOGUE_SCHEMA, route_dialogue
from services.network.federation_overlay import relay_federation_offer
from services.network.federation_overlay import enqueue_federated_proof_offered
from services.network.runtime import federation_overlay_status, overlay_status, reset_overlay_runtime
from tests.test_trust_policy_bundle import _minimal_proof


class FederationOverlayTests(unittest.TestCase):
    def setUp(self):
        self._persist_prev = os.environ.get("POCP_OVERLAY_PERSIST")
        os.environ["POCP_OVERLAY_PERSIST"] = "false"
        reset_overlay_runtime()
        self._env_backup = os.environ.get("POCP_TRUSTED_NODES")
        os.environ["POCP_TRUSTED_NODES"] = (
            '[{"node_id": "peer-a", "base_url": "http://peer-a:9000", "trust_weight": 0.9}]'
        )

        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.human = Entity(
            entity_type=EntityType.human,
            name="Alice",
            status=EntityStatus.active,
        )
        self.db.add(self.human)
        self.db.commit()
        self.proof = _minimal_proof()

    def tearDown(self):
        self.db.close()
        reset_overlay_runtime()
        if self._persist_prev is None:
            os.environ.pop("POCP_OVERLAY_PERSIST", None)
        else:
            os.environ["POCP_OVERLAY_PERSIST"] = self._persist_prev
        if self._env_backup is None:
            os.environ.pop("POCP_TRUSTED_NODES", None)
        else:
            os.environ["POCP_TRUSTED_NODES"] = self._env_backup

    def test_federation_overlay_status_lists_recent(self):
        enqueue_federated_proof_offered(
            source_node_id="peer-a",
            contribution_id="c1",
            proof=self.proof,
            validation={"blocking_valid": True},
            dialogue_id="dlg_x",
        )
        status = federation_overlay_status()
        self.assertEqual(status["federation"]["pending_federation_offers"], 1)
        self.assertEqual(len(status["federation"]["recent_federation_events"]), 1)
        self.assertEqual(status["pending_by_type"]["FederatedProofOffered"], 1)

    @patch("services.network.federation_overlay.fetch_peer_proof_http")
    def test_relay_inline_proof_enqueues_overlay(self, mock_fetch):
        result = relay_federation_offer(
            self.db,
            source_node_id="peer-a",
            proof=self.proof,
            auto_import=False,
        )
        mock_fetch.assert_not_called()
        self.assertEqual(result["mode"], "federation_relay")
        self.assertTrue(result["validation"]["blocking_valid"])
        self.assertIn("event_id", result["overlay_event"])
        self.assertEqual(overlay_status()["mempool_size"], 1)

    @patch("services.network.federation_overlay.fetch_peer_proof_http")
    def test_relay_fetches_from_peer(self, mock_fetch):
        mock_fetch.return_value = self.proof
        result = relay_federation_offer(
            self.db,
            source_node_id="peer-a",
            contribution_id="c1",
            auto_import=False,
        )
        mock_fetch.assert_called_once_with("http://peer-a:9000", "c1")
        self.assertEqual(result["contribution_id"], "c1")

    @patch("services.network.federation_overlay.fetch_peer_proof_http")
    def test_federation_offer_dialogue_with_inline_proof(self, mock_fetch):
        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_fed_1",
            "kind": "federation_offer",
            "from": {"entity_id": self.human.id, "node_id": "peer-a"},
            "to": {"entity_id": self.human.id, "node_id": "local"},
            "payload": {
                "source_node_id": "peer-a",
                "proof": self.proof,
                "fetch_peer": False,
            },
        }
        response = asyncio.run(route_dialogue(self.db, envelope))
        mock_fetch.assert_not_called()
        self.assertEqual(response["status"], "accepted")
        self.assertEqual(response["result"]["mode"], "federation_relay")
        self.assertIn("protocol_event_id", response["refs"])
        self.assertEqual(overlay_status()["mempool_size"], 1)

    @patch("services.network.federation_overlay.fetch_peer_proof_http")
    @patch("services.network.federation_overlay.import_from_proof_packet")
    def test_federation_accept_auto_import(self, mock_import, mock_fetch):
        mock_fetch.return_value = self.proof

        class _FakeImport:
            id = "fed_imp_1"
            primary_portable_id = "dev:alice"

        mock_import.return_value = _FakeImport()

        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_fed_acc_1",
            "kind": "federation_accept",
            "from": {"entity_id": self.human.id, "node_id": "peer-a"},
            "to": {"entity_id": self.human.id, "node_id": "local"},
            "payload": {
                "source_node_id": "peer-a",
                "contribution_id": "c1",
                "auto_import": True,
            },
        }
        response = asyncio.run(route_dialogue(self.db, envelope))
        self.assertEqual(response["status"], "accepted")
        self.assertTrue(response["result"]["import"]["imported"])
        mock_import.assert_called_once()


if __name__ == "__main__":
    unittest.main()
