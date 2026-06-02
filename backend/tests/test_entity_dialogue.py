"""Tests for Entity Dialogue Protocol (pocp.entity_dialogue.v0.1)."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.invocation import InvocationStep, InvocationTrace
from services.entity_dialogue import (
    ENTITY_DIALOGUE_SCHEMA,
    dialogue_manifest,
    route_dialogue,
    validate_dialogue_envelope,
)
from services.entity_register import register_entity


class EntityDialogueTests(unittest.TestCase):
    def setUp(self):
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
        self.db.close()

    def test_dialogue_manifest_has_kinds(self):
        manifest = dialogue_manifest()
        self.assertEqual(manifest["schema"], ENTITY_DIALOGUE_SCHEMA)
        self.assertIn("invoke", manifest["kinds"])
        self.assertIn("federation_offer", manifest["kinds"])
        self.assertEqual(manifest["transport"]["physical_network"], "none")

    def test_validate_envelope_rejects_bad_schema(self):
        result = validate_dialogue_envelope({"schema": "wrong", "kind": "ping"})
        self.assertFalse(result["ok"])
        self.assertTrue(any("schema" in e for e in result["errors"]))

    def test_ping_dialogue(self):
        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_ping_1",
            "kind": "ping",
            "from": {"entity_id": self.human.id, "node_id": "test-node"},
            "to": {"entity_id": self.human.id, "node_id": "test-node"},
        }
        response = route_dialogue(self.db, envelope)
        self.assertEqual(response["status"], "accepted")
        self.assertTrue(response["result"]["pong"])

    def test_discover_skill_entity(self):
        skill = register_entity(
            self.db,
            entity_type="skill",
            name="R-Tutor",
            description="Tutor skill",
            owner_id=self.human.id,
            creator_id=self.human.id,
        )
        self.db.commit()

        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_disc_1",
            "kind": "discover",
            "from": {"entity_id": self.human.id, "node_id": "test-node"},
            "to": {"entity_id": skill.id, "node_id": "test-node"},
        }
        response = route_dialogue(self.db, envelope)
        self.assertEqual(response["status"], "accepted")
        self.assertEqual(response["result"]["entity"]["entity_id"], skill.id)
        self.assertIn("dialogue", response["bindings"])

    def test_invoke_records_invocation_step(self):
        skill = register_entity(
            self.db,
            entity_type="skill",
            name="Invoke Skill",
            description="Skill",
            owner_id=self.human.id,
            creator_id=self.human.id,
        )
        self.db.commit()

        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_inv_1",
            "kind": "invoke",
            "from": {"entity_id": self.human.id, "node_id": "test-node"},
            "to": {"entity_id": skill.id, "node_id": "test-node"},
            "payload": {"input": {"topic": "PoCP"}},
        }
        response = route_dialogue(self.db, envelope)
        self.assertEqual(response["status"], "accepted")
        trace_id = response["refs"]["invocation_trace_id"]
        self.assertIsNotNone(trace_id)

        trace = self.db.query(InvocationTrace).filter(InvocationTrace.id == trace_id).first()
        self.assertIsNotNone(trace)
        steps = self.db.query(InvocationStep).filter(InvocationStep.trace_id == trace_id).all()
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].action, "uses")
        self.assertEqual(steps[0].source_entity_id, self.human.id)
        self.assertEqual(steps[0].target_entity_id, skill.id)

    def test_invoke_rejects_invalid_edge(self):
        agent = register_entity(
            self.db,
            entity_type="agent",
            name="Study Agent",
            description="Agent",
            owner_id=self.human.id,
            creator_id=self.human.id,
        )
        self.db.commit()

        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_bad_1",
            "kind": "invoke",
            "from": {"entity_id": self.human.id, "node_id": "test-node"},
            "to": {"entity_id": agent.id, "node_id": "test-node"},
            "payload": {"action": "calls"},
        }
        response = route_dialogue(self.db, envelope)
        self.assertEqual(response["status"], "rejected")

    def test_entity_target_mismatch_rejected(self):
        skill = register_entity(
            self.db,
            entity_type="skill",
            name="Target Skill",
            description="Skill",
            owner_id=self.human.id,
            creator_id=self.human.id,
        )
        self.db.commit()

        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_mismatch",
            "kind": "discover",
            "from": {"entity_id": self.human.id, "node_id": "test-node"},
            "to": {"entity_id": skill.id, "node_id": "test-node"},
        }
        response = route_dialogue(
            self.db,
            envelope,
            expected_target_entity_id="wrong-entity-id",
        )
        self.assertEqual(response["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
