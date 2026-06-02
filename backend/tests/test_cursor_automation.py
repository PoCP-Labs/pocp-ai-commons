"""Cursor automation — handoff pick + prompt build (no live Cursor API)."""

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from meta_agents_spec import NEXUS_ID
from models.agent_studio import StudioHandoffStatus
from services.agent_studio.cursor_bridge import build_handoff_prompt
from services.agent_studio.cursor_automation import pick_pending_handoffs, run_cursor_automation_tick
from services.agent_studio.handoffs import create_handoff
from services.meta_agent_registry import ensure_meta_agents


class CursorAutomationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        ensure_meta_agents(self.db)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_build_handoff_prompt_includes_scope(self):
        text = build_handoff_prompt(
            handoff_id="h1",
            to_agent_entity_id="pocp-agent-vault-0",
            scope="Fix wallet audit",
            tests_run="pytest -k wallet",
            mission_id="m1",
        )
        self.assertIn("Vault-0", text)
        self.assertIn("Fix wallet audit", text)
        self.assertIn("pytest -k wallet", text)

    def test_pick_skips_nexus_assignee(self):
        create_handoff(
            self.db,
            from_agent_entity_id=NEXUS_ID,
            to_agent_entity_id=NEXUS_ID,
            scope="integrate",
        )
        create_handoff(
            self.db,
            from_agent_entity_id=NEXUS_ID,
            to_agent_entity_id="pocp-agent-vault-0",
            scope="wallet work",
        )
        self.db.commit()
        picked = pick_pending_handoffs(self.db, limit=5)
        self.assertEqual(len(picked), 1)
        self.assertEqual(picked[0].to_agent_entity_id, "pocp-agent-vault-0")

    @patch("services.agent_studio.cursor_automation.automation_enabled", return_value=True)
    @patch("services.agent_studio.cursor_automation.execute_handoff_prompt")
    @patch("services.agent_studio.nexus_autopilot.run_nexus_autopilot")
    def test_tick_completes_handoff_on_success(self, mock_nexus, mock_exec, _enabled):
        mock_exec.return_value = {"ok": True, "status": "finished", "summary": "done", "run_id": "r1"}
        mock_nexus.return_value = {"mode": "monitor"}
        create_handoff(
            self.db,
            from_agent_entity_id=NEXUS_ID,
            to_agent_entity_id="pocp-agent-gauge-0",
            scope="run tests",
        )
        self.db.commit()
        tick = run_cursor_automation_tick(self.db, max_handoffs=1)
        self.assertTrue(tick["ran"])
        self.assertEqual(len(tick["processed"]), 1)
        self.assertEqual(tick["processed"][0]["status"], "completed")
        handoff = pick_pending_handoffs(self.db)
        self.assertEqual(len(handoff), 0)


if __name__ == "__main__":
    unittest.main()
