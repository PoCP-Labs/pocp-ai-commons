"""Agent Studio mission plan tests."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from services.agent_studio.mission_plans import create_mission_from_plan, spawn_plan_handoffs
from services.agent_studio.missions import create_mission
from services.meta_agent_registry import ensure_meta_agents


class AgentStudioPlanTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        ensure_meta_agents(self.db)

    def tearDown(self):
        self.db.close()

    def test_spawn_phase_a_p0_handoffs(self):
        mission = create_mission(self.db, title="Test P0", kind="improve")
        handoffs = spawn_plan_handoffs(self.db, mission.id, "phase_a_p0")
        self.assertEqual(len(handoffs), 6)
        self.assertEqual(handoffs[0]["from_agent_entity_id"], "pocp-agent-nexus-0")

    def test_create_mission_from_plan(self):
        result = create_mission_from_plan(self.db, "phase_a_p0")
        self.assertEqual(result["plan_id"], "phase_a_p0")
        self.assertEqual(result["handoff_count"], 6)
        self.assertEqual(result["mission"]["status"], "active")

    def test_spawn_phase_a_kernel_handoffs(self):
        result = create_mission_from_plan(self.db, "phase_a_kernel")
        self.assertEqual(result["plan_id"], "phase_a_kernel")
        self.assertEqual(result["handoff_count"], 10)
        scopes = " ".join(h["scope"] for h in result["handoffs"])
        self.assertIn("PA-1", scopes)
        self.assertIn("PA-4", scopes)

    def test_protocol_layer_edp_plan_handoffs(self):
        result = create_mission_from_plan(self.db, "protocol_layer_edp")
        self.assertEqual(result["plan_id"], "protocol_layer_edp")
        self.assertEqual(result["handoff_count"], 10)
        scopes = " ".join(h["scope"] for h in result["handoffs"])
        self.assertIn("PL-1", scopes)
        self.assertIn("PL-10", scopes)


if __name__ == "__main__":
    unittest.main()
