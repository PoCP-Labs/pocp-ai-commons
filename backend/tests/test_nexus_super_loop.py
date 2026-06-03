"""Nexus super-loop (plan → Cursor → PDCA → heal)."""

import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from services.agent_studio.nexus_super_loop import (
    cursor_backend_automation_enabled,
    run_nexus_super_tick,
    super_loop_backend_enabled,
    super_loop_status,
)
from services.meta_agent_registry import ensure_meta_agents


class NexusSuperLoopTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        ensure_meta_agents(self.db)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    @patch("services.agent_studio.nexus_super_loop.run_cursor_automation_tick")
    @patch("services.agent_studio.nexus_super_loop.automation_enabled", return_value=False)
    @patch("services.agent_studio.nexus_super_loop.probe_platform")
    def test_super_tick_without_cursor(self, mock_probe, _auto, _cursor):
        mock_probe.return_value = {"ok": True, "issues": []}
        result = run_nexus_super_tick(self.db, max_cursor_handoffs=0)
        self.assertTrue(result["ran"])
        self.assertTrue(result["super_loop"])
        self.assertIn("nexus", result)
        self.assertEqual(result["cursor"]["processed_count"], 0)
        self.assertFalse(result["human_required"])

    @patch("services.agent_studio.nexus_super_loop.run_cursor_automation_tick")
    @patch("services.agent_studio.nexus_super_loop.automation_enabled", return_value=False)
    @patch("services.agent_studio.nexus_super_loop.probe_platform")
    def test_super_tick_dispatches_repair_on_unhealthy(self, mock_probe, _auto, _cursor):
        mock_probe.return_value = {"ok": False, "issues": ["db: connection refused"]}
        result = run_nexus_super_tick(self.db, max_cursor_handoffs=0)
        heal = next((s for s in result["steps"] if s.get("phase") == "heal_platform"), None)
        self.assertIsNotNone(heal)
        self.assertGreater(len(heal.get("handoffs") or []), 0)
        self.assertTrue(result["human_required"])

    @patch("services.agent_studio.nexus_super_loop.run_cursor_automation_tick")
    @patch("services.agent_studio.nexus_super_loop.automation_enabled", return_value=False)
    @patch("services.agent_studio.nexus_super_loop.probe_platform")
    def test_super_tick_dispatches_gauge_repair_on_api_timeout(self, mock_probe, _auto, _cursor):
        mock_probe.return_value = {
            "ok": False,
            "issues": ["api: timed out"],
            "api": {"ok": False, "detail": "timed out", "base": "http://127.0.0.1:8008"},
            "database": {"ok": True, "detail": "postgres ping ok"},
        }
        result = run_nexus_super_tick(self.db, max_cursor_handoffs=0)
        heal = next((s for s in result["steps"] if s.get("phase") == "heal_platform"), None)
        self.assertIsNotNone(heal)
        assignees = {h.get("assignee") for h in heal.get("handoffs") or []}
        self.assertIn("pocp-agent-gauge-0", assignees)
        self.assertTrue(result["human_required"])

    def test_super_loop_status_shape(self):
        status = super_loop_status()
        self.assertIn("enabled", status)
        self.assertIn("host_mode", status)
        self.assertIn("interval_sec", status)
        self.assertIn("max_cursor_per_tick", status)

    def test_host_mode_disables_backend_loops(self):
        with patch.dict(
            os.environ,
            {
                "POCP_NEXUS_SUPER_LOOP_HOST": "true",
                "POCP_NEXUS_SUPER_LOOP": "true",
                "POCP_CURSOR_AUTOMATION": "true",
            },
            clear=False,
        ):
            self.assertFalse(super_loop_backend_enabled())
            self.assertFalse(cursor_backend_automation_enabled())


if __name__ == "__main__":
    unittest.main()
