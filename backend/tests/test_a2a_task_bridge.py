"""Tests for A2A JSON-RPC task bridge (BI-1.5)."""

import unittest
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401
from database import Base
from models.contribution import ContributionEvent, ContributionStatus
from models.entity import Entity, EntityStatus, EntityType
from models.task import Task
from services.a2a_task_bridge import (
    extract_message_text,
    handle_jsonrpc_call,
    map_contribution_status_to_a2a_state,
    send_message_to_contribution,
)


class A2ATaskBridgeTests(unittest.TestCase):
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
        self.agent = Entity(
            entity_type=EntityType.agent,
            name="Study Bot",
            status=EntityStatus.active,
        )
        self.db.add_all([self.human, self.agent])
        self.db.flush()
        self.agent.owner_id = self.human.id

        self.task = Task(
            title="Research sprint",
            description="Demo task",
            sponsor_id=self.human.id,
        )
        self.db.add(self.task)
        self.db.commit()

        self.user = SimpleNamespace(id="user-1", entity_id=self.human.id)

    def tearDown(self):
        self.db.close()

    def test_extract_message_text_from_parts(self):
        text = extract_message_text(
            {
                "role": "ROLE_USER",
                "parts": [{"kind": "text", "text": "Hello PoCP"}],
            }
        )
        self.assertEqual(text, "Hello PoCP")

    def test_send_message_creates_contribution(self):
        contribution = send_message_to_contribution(
            self.db,
            user=self.user,
            params={
                "message": {
                    "role": "ROLE_USER",
                    "parts": [{"kind": "text", "text": "Knowledge for the commons."}],
                },
                "metadata": {
                    "taskId": self.task.id,
                    "contributionType": "knowledge",
                    "contextId": "ctx-1",
                },
            },
            target_entity_id=self.agent.id,
        )
        self.db.commit()
        self.assertEqual(contribution.primary_entity_id, self.human.id)
        self.assertEqual(contribution.task_id, self.task.id)
        self.assertEqual(contribution.status, ContributionStatus.submitted)
        self.assertIn("a2a", (contribution.evidence or {}).get("_pocp", {}))
        roles = {p.role.value for p in contribution.participants}
        self.assertIn("creator", roles)
        self.assertIn("executor", roles)

    def test_jsonrpc_send_message_and_get_task(self):
        send_resp = handle_jsonrpc_call(
            self.db,
            user=self.user,
            payload={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "SendMessage",
                "params": {
                    "message": {
                        "parts": [{"kind": "text", "text": "Bridge test contribution content."}],
                    },
                    "metadata": {"taskId": self.task.id},
                },
            },
            target_entity_id=self.agent.id,
        )
        self.assertNotIn("error", send_resp)
        task = send_resp["result"]["task"]
        self.assertEqual(task["status"]["state"], "TASK_STATE_SUBMITTED")
        self.assertFalse(task["metadata"]["humanFinalizationRequired"])
        self.assertTrue(task["metadata"]["autoFinalizationEnabled"])

        get_resp = handle_jsonrpc_call(
            self.db,
            user=self.user,
            payload={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "GetTask",
                "params": {"id": task["id"]},
            },
        )
        self.assertEqual(get_resp["result"]["id"], task["id"])

    def test_get_task_not_found(self):
        resp = handle_jsonrpc_call(
            self.db,
            user=self.user,
            payload={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "GetTask",
                "params": {"id": "missing"},
            },
        )
        self.assertEqual(resp["error"]["code"], -32001)

    def test_status_mapping_ai_verified(self):
        self.assertEqual(
            map_contribution_status_to_a2a_state(ContributionStatus.ai_verified),
            "TASK_STATE_WORKING",
        )


if __name__ == "__main__":
    unittest.main()
