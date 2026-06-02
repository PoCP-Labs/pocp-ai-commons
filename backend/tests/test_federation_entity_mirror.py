"""Tests for mirroring remote node entities locally."""

import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from services.federation_entity_mirror import (
    mirror_peer_entities,
    remote_mirror_entity_id,
    resolve_mirror_for_dialogue,
)
from services.network.dialogue_route import try_peer_route_dialogue


class FederationEntityMirrorTests(unittest.TestCase):
    def setUp(self):
        self._trusted_prev = os.environ.get("POCP_TRUSTED_NODES")
        os.environ["POCP_TRUSTED_NODES"] = (
            '[{"node_id": "node-b", "base_url": "https://peer-b.example.com", "trust_weight": 0.9}]'
        )
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        if self._trusted_prev is None:
            os.environ.pop("POCP_TRUSTED_NODES", None)
        else:
            os.environ["POCP_TRUSTED_NODES"] = self._trusted_prev

    def test_remote_mirror_entity_id_stable(self):
        a = remote_mirror_entity_id("node-b", "remote-uuid-1")
        b = remote_mirror_entity_id("node-b", "remote-uuid-1")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 36)

    @patch("services.federation_entity_mirror.fetch_peer_entity_catalog")
    def test_mirror_creates_shadow_entities(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "id": "skill-on-b-001",
                "entity_type": "skill",
                "name": "Summarize",
                "description": "Remote skill",
            }
        ]
        result = mirror_peer_entities(self.db, "node-b", entity_types=["skill"])
        self.db.commit()
        self.assertEqual(result["created"], 1)
        local_id = result["entities"][0]["local_entity_id"]
        row = self.db.get(Entity, local_id)
        self.assertIsNotNone(row)
        self.assertEqual(row.entity_type, EntityType.skill)
        self.assertIn("federated_mirror", row.metadata_["roles"])

    @patch("services.federation_entity_mirror.fetch_peer_entity_catalog")
    def test_resolve_mirror_for_dialogue(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "id": "skill-on-b-002",
                "entity_type": "skill",
                "name": "Translate",
            }
        ]
        mirror_peer_entities(self.db, "node-b", entity_types=["skill"])
        self.db.commit()
        local_id = remote_mirror_entity_id("node-b", "skill-on-b-002")
        hints = resolve_mirror_for_dialogue(self.db, local_id)
        self.assertEqual(hints["home_node_id"], "node-b")
        self.assertEqual(hints["remote_entity_id"], "skill-on-b-002")

    @patch("services.network.dialogue_route._post_json")
    @patch("services.federation_entity_mirror.fetch_peer_entity_catalog")
    def test_try_peer_route_rewrites_mirror_target(self, mock_fetch, mock_post):
        os.environ["POCP_DIALOGUE_PEER_ROUTE"] = "true"
        mock_fetch.return_value = [
            {"id": "skill-remote", "entity_type": "skill", "name": "Remote"},
        ]
        mirror_peer_entities(self.db, "node-b", entity_types=["skill"])
        self.db.commit()
        local_id = remote_mirror_entity_id("node-b", "skill-remote")
        mock_post.return_value = {"status": "accepted", "result": {}}

        envelope = {
            "kind": "ping",
            "to": {"entity_id": local_id},
            "payload": {},
        }

        with patch("services.network.dialogue_route.local_node_id", return_value="node-a"):
            with patch("services.network.dialogue_route.peer_route_enabled", return_value=True):
                out = try_peer_route_dialogue(
                    self.db,
                    envelope,
                    resolve_target=lambda _db, _ref: None,
                )
        self.assertIsNotNone(out)
        posted = mock_post.call_args[0][1]
        self.assertEqual(posted["to"]["node_id"], "node-b")
        self.assertEqual(posted["to"]["entity_id"], "skill-remote")


if __name__ == "__main__":
    unittest.main()
