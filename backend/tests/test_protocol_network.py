"""Tests for Protocol Event Network overlay + dialogue bridge."""

import asyncio
import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from services.entity_dialogue import ENTITY_DIALOGUE_SCHEMA, route_dialogue
from services.entity_register import register_entity
from services.network.protocol_bridge import (
    protocol_event_from_dialogue,
    protocol_event_to_dict,
)
from services.network.runtime import enqueue_event, overlay_status, reset_overlay_runtime, seal_batch
from services.network.types import ProtocolEvent


class ProtocolBridgeTests(unittest.TestCase):
    def test_invoke_maps_to_invocation_created(self):
        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_bridge_1",
            "kind": "invoke",
            "from": {"entity_id": "h1", "node_id": "node-a"},
            "to": {"entity_id": "s1", "node_id": "node-a"},
            "payload": {"action": "uses"},
        }
        event = protocol_event_from_dialogue(envelope)
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.event_type, "InvocationCreated")

    def test_broadcast_custom_event_type(self):
        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_bc_1",
            "kind": "broadcast",
            "from": {"entity_id": "h1", "node_id": "node-a"},
            "to": {"entity_id": "s1", "node_id": "node-a"},
            "payload": {
                "event_type": "CustomPing",
                "event_payload": {"hello": True},
            },
        }
        event = protocol_event_from_dialogue(envelope)
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.event_type, "CustomPing")


class OverlayRuntimeTests(unittest.TestCase):
    def setUp(self):
        self._persist_prev = os.environ.get("POCP_OVERLAY_PERSIST")
        os.environ["POCP_OVERLAY_PERSIST"] = "false"
        reset_overlay_runtime()

    def tearDown(self):
        reset_overlay_runtime()
        if self._persist_prev is None:
            os.environ.pop("POCP_OVERLAY_PERSIST", None)
        else:
            os.environ["POCP_OVERLAY_PERSIST"] = self._persist_prev

    def test_enqueue_and_seal_batch(self):
        event = ProtocolEvent.create("TestEvent", {"x": 1}, entity_id="e1", node_id="n1")
        enqueue_event(event)
        status = overlay_status()
        self.assertEqual(status["mempool_size"], 1)
        sealed = seal_batch(created_by_node_id="n1")
        self.assertTrue(sealed["sealed"])
        self.assertEqual(sealed["event_count"], 1)
        self.assertIn("event_merkle_root", sealed["batch"])


class DialogueOverlayEmitTests(unittest.TestCase):
    def setUp(self):
        self._persist_prev = os.environ.get("POCP_OVERLAY_PERSIST")
        os.environ["POCP_OVERLAY_PERSIST"] = "false"
        reset_overlay_runtime()
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

    def tearDown(self):
        reset_overlay_runtime()
        if self._persist_prev is None:
            os.environ.pop("POCP_OVERLAY_PERSIST", None)
        else:
            os.environ["POCP_OVERLAY_PERSIST"] = self._persist_prev
        self.db.close()

    def test_invoke_emits_overlay_event(self):
        skill = register_entity(
            self.db,
            entity_type="skill",
            name="Skill",
            description="S",
            owner_id=self.human.id,
            creator_id=self.human.id,
        )
        self.db.commit()

        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_overlay_1",
            "kind": "invoke",
            "from": {"entity_id": self.human.id, "node_id": "test-node"},
            "to": {"entity_id": skill.id, "node_id": "test-node"},
            "payload": {},
        }
        response = asyncio.run(route_dialogue(self.db, envelope))
        self.assertEqual(response["status"], "accepted")
        self.assertIn("protocol_event_id", response.get("refs") or {})
        self.assertEqual(overlay_status()["mempool_size"], 1)


if __name__ == "__main__":
    unittest.main()
