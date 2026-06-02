"""Nexus-0 learning, review, and coaching."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from meta_agents_spec import NEXUS_ID
from models.agent import Agent
from services.agent_studio.nexus_learning import (
    review_project_progress,
    run_nexus_learning_cycle,
)
from services.meta_agent_registry import ensure_meta_agents


class NexusLearningTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        ensure_meta_agents(self.db)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_progress_review_lists_agents(self):
        report = review_project_progress(self.db)
        self.assertEqual(report["reviewer_entity_id"], NEXUS_ID)
        self.assertGreaterEqual(len(report["agent_health"]), 14)
        self.assertIn("completion_percent", report)

    def test_learning_cycle_updates_nexus_profile(self):
        result = run_nexus_learning_cycle(self.db)
        self.db.commit()
        self.assertTrue(result["learning_cycle"])
        self.assertTrue(result["self_study"]["self_study"])
        agent = self.db.query(Agent).filter(Agent.entity_id == NEXUS_ID).first()
        profile = (agent.config or {}).get("learning_profile", {})
        self.assertIn("research_log", profile)
        self.assertIn("coaching_log", profile)


if __name__ == "__main__":
    unittest.main()
