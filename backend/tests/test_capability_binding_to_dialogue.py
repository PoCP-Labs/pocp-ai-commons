"""Tests for REST/A2A → dialogue binding map and A2A deferred submit (PL-5)."""

import unittest
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401
from database import Base
from models.contribution import ContributionStatus
from models.entity import Entity, EntityStatus, EntityType
from models.task import Task
from services.a2a_task_bridge import send_message_to_contribution
from services.capability.a2a_deferred_submit import apply_a2a_deferred_submit_binding
from services.capability.binding_to_dialogue import (
    A2A_SENDMESSAGE_BINDING_KEY,
    A2A_SENDMESSAGE_DIALOGUE_KIND,
    binding_map_manifest,
    dialogue_kind_for_binding,
)
from services.evidence import POCP_META_KEY
from services.network.runtime import reset_overlay_runtime


class BindingToDialogueTests(unittest.TestCase):
    def setUp(self):
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
        self.agent = Entity(
            entity_type=EntityType.agent,
            name="Study Bot",
            status=EntityStatus.active,
        )
        self.db.add_all([self.human, self.agent])
        self.db.flush()
        self.agent.owner_id = self.human.id

        self.task = Task(
            title="Binding test",
            description="PL-5",
            sponsor_id=self.human.id,
        )
        self.db.add(self.task)
        self.db.commit()
        self.user = SimpleNamespace(id="user-1", entity_id=self.human.id)

    def tearDown(self):
        self.db.close()
        reset_overlay_runtime()

    def test_binding_map_includes_a2a_send_message_deferred(self):
        manifest = binding_map_manifest()
        a2a = manifest["a2a"]["SendMessage"]
        self.assertEqual(a2a["dialogue_kind"], "submit")
        self.assertEqual(a2a["binding_mode"], "deferred")
        self.assertEqual(dialogue_kind_for_binding(A2A_SENDMESSAGE_BINDING_KEY), "submit")

    def test_send_message_stamps_deferred_submit_binding(self):
        contribution = send_message_to_contribution(
            self.db,
            user=self.user,
            params={
                "message": {"parts": [{"kind": "text", "text": "Deferred submit binding."}]},
                "metadata": {"taskId": self.task.id},
            },
            target_entity_id=self.agent.id,
        )
        self.db.commit()
        pocp = (contribution.evidence or {}).get(POCP_META_KEY) or {}
        self.assertEqual(pocp.get("dialogue_kind"), A2A_SENDMESSAGE_DIALOGUE_KIND)
        self.assertEqual(pocp.get("binding"), A2A_SENDMESSAGE_BINDING_KEY)
        self.assertEqual(pocp.get("binding_mode"), "deferred")
        self.assertTrue(str(pocp.get("dialogue_id", "")).startswith("dlg_"))
        self.assertEqual(contribution.status, ContributionStatus.submitted)

    def test_apply_deferred_submit_overlay_event_id(self):
        from services.contribution_submit import submit_contribution_event

        contribution = submit_contribution_event(
            self.db,
            human_entity_id=self.human.id,
            task_id=self.task.id,
            contribution_type="knowledge",
            description="overlay test",
            evidence={"content_preview": "overlay test evidence"},
            participants=[],
        )
        dialogue_id = apply_a2a_deferred_submit_binding(
            self.db,
            contribution,
            human_entity_id=self.human.id,
            target_entity_id=self.agent.id,
            enqueue_overlay=True,
        )
        self.db.commit()
        pocp = (contribution.evidence or {}).get(POCP_META_KEY) or {}
        self.assertEqual(pocp.get("dialogue_id"), dialogue_id)
        self.assertIn("protocol_event_id", pocp)


if __name__ == "__main__":
    unittest.main()
