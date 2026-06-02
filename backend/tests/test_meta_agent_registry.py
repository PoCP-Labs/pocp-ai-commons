"""Meta Agent entity registration tests."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from meta_agents_spec import META_AGENT_IDS, NEXUS_ID
from models.agent import Agent
from models.entity import Entity
from services.meta_agent_registry import (
    ensure_meta_agents,
    get_meta_agent,
    list_meta_agents,
    meta_agent_roster_summary,
)


class MetaAgentRegistryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()

    def test_ensure_registers_all_meta_agents(self):
        ids = ensure_meta_agents(self.db)
        self.assertEqual(len(ids), len(META_AGENT_IDS))
        for eid in META_AGENT_IDS:
            entity = self.db.get(Entity, eid)
            self.assertIsNotNone(entity, eid)
            self.assertEqual(entity.entity_type.value, "agent")
            agent = self.db.query(Agent).filter(Agent.entity_id == eid).first()
            self.assertIsNotNone(agent)
            self.assertTrue(agent.config.get("meta_agent"))

    def test_nexus_orchestrates_others(self):
        ensure_meta_agents(self.db)
        nexus = get_meta_agent(self.db, NEXUS_ID)
        self.assertIsNotNone(nexus)
        self.assertIsNone(nexus["reports_to"])
        orchestrates = nexus["orchestrates"]
        self.assertGreater(len(orchestrates), 10)
        self.assertIn("pocp-agent-forge-0", orchestrates)

    def test_forge_reports_to_nexus(self):
        ensure_meta_agents(self.db)
        forge = get_meta_agent(self.db, "pocp-agent-forge-0")
        self.assertEqual(forge["reports_to"], NEXUS_ID)
        self.assertIn("contribution_submit", forge["capabilities"])

    def test_list_meta_agents_sorted(self):
        ensure_meta_agents(self.db)
        rows = list_meta_agents(self.db)
        self.assertEqual(len(rows), len(META_AGENT_IDS))
        names = [r["name"] for r in rows]
        self.assertEqual(names, sorted(names))

    def test_roster_summary_static(self):
        summary = meta_agent_roster_summary()
        self.assertEqual(summary["count"], len(META_AGENT_IDS))
        self.assertEqual(summary["nexus_id"], NEXUS_ID)


if __name__ == "__main__":
    unittest.main()
