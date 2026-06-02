"""Nexus-0 autonomous PM autopilot."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.agent_studio import AgentStudioMission, StudioMissionStatus
from services.agent_studio.nexus_autopilot import (
    nexus_pm_status,
    run_nexus_autopilot,
)
from services.meta_agent_registry import ensure_meta_agents


class NexusAutopilotTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        ensure_meta_agents(self.db)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_autopilot_starts_phase_a_p0(self):
        result = run_nexus_autopilot(self.db)
        self.db.commit()
        self.assertIn(result["mode"], ("dispatched", "monitor", "advanced"))
        self.assertGreater(result["pending_handoff_count"], 0)
        self.assertTrue(result["dispatch_queue"])
        active = (
            self.db.query(AgentStudioMission)
            .filter(AgentStudioMission.status == StudioMissionStatus.active)
            .count()
        )
        self.assertEqual(active, 1)

    def test_autopilot_idempotent_monitor(self):
        run_nexus_autopilot(self.db)
        self.db.commit()
        second = run_nexus_autopilot(self.db)
        self.assertEqual(second["mode"], "monitor")
        self.assertGreater(second["pending_handoff_count"], 0)

    def test_nexus_pm_status_includes_goals(self):
        status = nexus_pm_status(self.db)
        self.assertEqual(status["orchestrator_entity_id"], "pocp-agent-nexus-0")
        self.assertGreaterEqual(len(status["goals"]), 6)


if __name__ == "__main__":
    unittest.main()
