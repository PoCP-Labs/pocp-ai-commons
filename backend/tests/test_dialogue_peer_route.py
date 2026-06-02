"""Tests for cross-node dialogue routing over trusted peers."""

import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from services.entity_dialogue import ENTITY_DIALOGUE_SCHEMA, route_dialogue
from services.entity_register import register_entity
from services.network.dialogue_route import (
    forward_dialogue_to_peer,
    should_route_to_peer,
    try_peer_route_dialogue,
    wrap_peer_route_response,
)
from services.federation_community import peer_entity_id


class DialoguePeerRouteTests(unittest.TestCase):
    def setUp(self):
        self._route_prev = os.environ.get("POCP_DIALOGUE_PEER_ROUTE")
        self._trusted_prev = os.environ.get("POCP_TRUSTED_NODES")
        os.environ["POCP_DIALOGUE_PEER_ROUTE"] = "true"
        os.environ["POCP_TRUSTED_NODES"] = (
            '[{"node_id": "node-b", "base_url": "https://peer-b.example.com", "trust_weight": 0.9}]'
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

        with patch("services.network.dialogue_route.local_node_id", return_value="node-a"):
            self._local_patch = patch("services.entity_dialogue._node_id", return_value="node-a")
            self._local_patch.start()

    def tearDown(self):
        self._local_patch.stop()
        self.db.close()
        if self._route_prev is None:
            os.environ.pop("POCP_DIALOGUE_PEER_ROUTE", None)
        else:
            os.environ["POCP_DIALOGUE_PEER_ROUTE"] = self._route_prev
        if self._trusted_prev is None:
            os.environ.pop("POCP_TRUSTED_NODES", None)
        else:
            os.environ["POCP_TRUSTED_NODES"] = self._trusted_prev

    def test_should_route_when_target_not_local(self):
        envelope = {
            "kind": "invoke",
            "to": {"portable_id": "skill:remote", "node_id": "node-b"},
            "payload": {},
        }
        with patch("services.network.dialogue_route.local_node_id", return_value="node-a"):
            route, peer = should_route_to_peer(envelope, target_resolved_locally=False)
        self.assertTrue(route)
        self.assertEqual(peer, "node-b")

    @patch("services.network.dialogue_route._post_json")
    def test_route_invoke_forwards_to_peer(self, mock_post):
        skill = register_entity(
            self.db,
            entity_type="skill",
            name="Local Copy",
            description="Should not use",
            owner_id=self.human.id,
            creator_id=self.human.id,
        )
        self.db.commit()

        mock_post.return_value = {
            "schema": "pocp.entity_dialogue_response.v0.1",
            "status": "accepted",
            "result": {"executed": False, "message": "ok on B"},
            "refs": {"invocation_trace_id": "trace-b"},
        }

        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_peer_1",
            "kind": "invoke",
            "from": {"entity_id": self.human.id, "node_id": "node-a"},
            "to": {"entity_id": skill.id, "node_id": "node-b", "portable_id": "skill:only-on-b"},
            "payload": {"route_peer": True, "input": "hi"},
        }
        import asyncio

        response = asyncio.run(route_dialogue(self.db, envelope))
        self.assertEqual(response["status"], "accepted")
        self.assertTrue(response["result"].get("peer_route"))
        mock_post.assert_called_once()
        url = mock_post.call_args[0][0]
        self.assertIn("peer-b.example.com", url)
        self.assertIn("/federation/dialogue", url)

    def test_wrap_peer_route_response(self):
        remote = {"status": "accepted", "result": {"pong": True}}
        wrapped = wrap_peer_route_response(
            {},
            remote,
            peer={"node_id": "node-b", "base_url": "https://peer-b.example.com"},
        )
        self.assertTrue(wrapped["result"]["peer_route"])

    @patch("services.network.dialogue_route._post_json")
    def test_route_uses_discovered_peer_when_not_trusted(self, mock_post):
        os.environ["POCP_TRUSTED_NODES"] = "[]"
        discovered = Entity(
            id=peer_entity_id("node-x"),
            entity_type=EntityType.community,
            name="Federation Peer · node-x",
            status=EntityStatus.active,
            metadata_={
                "roles": ["federation_peer", "discovered_peer"],
                "node_id": "node-x",
                "base_url": "https://peer-x.example.com",
                "trust_weight": 0.7,
            },
        )
        self.db.add(discovered)
        self.db.commit()
        mock_post.return_value = {"status": "accepted", "result": {"pong": True}}
        envelope = {
            "kind": "ping",
            "to": {"node_id": "node-x", "portable_id": "skill:x"},
            "payload": {"route_peer": True},
        }
        with patch("services.network.dialogue_route.local_node_id", return_value="node-a"):
            out = try_peer_route_dialogue(self.db, envelope, resolve_target=lambda _db, _ref: None)
        self.assertEqual(out["status"], "accepted")
        url = mock_post.call_args[0][0]
        self.assertIn("peer-x.example.com", url)


if __name__ == "__main__":
    unittest.main()
