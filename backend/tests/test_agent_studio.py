"""Agent Studio sub-platform tests."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from meta_agents_spec import NEXUS_ID
from services.agent_studio.evolution import (
    apply_proposal,
    get_learning_profile,
    process_outcome,
    review_proposal,
    studio_dashboard,
)
from services.agent_studio.handoffs import create_handoff
from services.agent_studio.missions import activate_mission, create_mission
from services.agent_studio.outcomes import record_outcome
from services.meta_agent_registry import ensure_meta_agents


class AgentStudioTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        ensure_meta_agents(self.db)

    def tearDown(self):
        self.db.close()

    def test_evolution_loop_failure_creates_proposal(self):
        mission = create_mission(
            self.db,
            title="Phase A hardening",
            kind="improve",
            orchestrator_entity_id=NEXUS_ID,
        )
        activate_mission(self.db, mission.id)
        handoff = create_handoff(
            self.db,
            from_agent_entity_id="pocp-agent-vault-0",
            to_agent_entity_id=NEXUS_ID,
            mission_id=mission.id,
            scope="Fix wallet audit",
        )
        outcome = record_outcome(
            self.db,
            agent_entity_id="pocp-agent-vault-0",
            kind="acceptance",
            result="fail",
            mission_id=mission.id,
            handoff_id=handoff.id,
            summary="acceptance runner red on wallet audit",
        )
        proposal = process_outcome(self.db, outcome.id)
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal.status.value, "pending_review")

        review_proposal(
            self.db,
            proposal.id,
            approve=True,
            reviewer_entity_id="pocp-agent-gauge-0",
        )
        result = apply_proposal(
            self.db, proposal.id, actor_entity_id="pocp-agent-nexus-0"
        )
        self.assertEqual(result["evolution_version"], 1)
        profile = get_learning_profile(self.db, "pocp-agent-vault-0")
        self.assertEqual(profile["applied_proposals"], 1)

    def test_dashboard_includes_meta_agents(self):
        dash = studio_dashboard(self.db)
        self.assertEqual(dash["platform"], "agent_studio")
        self.assertGreaterEqual(dash["stats"]["meta_agents"], 15)
        self.assertIn("learn", dash["pillars"])


if __name__ == "__main__":
    unittest.main()
