"""Agent Studio memory vault and auto-evolution."""

import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from services.agent_studio.auto_evolution import ingest_handoff_memory, run_auto_evolution_tick
from services.agent_studio.handoffs import complete_handoff, create_handoff
from services.agent_studio.memory_store import append_memory, list_memories, vault_summary
from services.agent_studio.agent_capabilities import evolve_capability, get_agent_capabilities
from services.meta_agent_registry import ensure_meta_agents
from meta_agents_spec import NEXUS_ID


class AgentStudioMemoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        ensure_meta_agents(self.db)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_append_and_list_memory(self):
        entry = append_memory(
            self.db,
            agent_entity_id="pocp-agent-forge-0",
            title="Test memory",
            content="Forge completed auth module",
            kind="semantic",
            sync_file=False,
        )
        self.db.commit()
        rows = list_memories(self.db, agent_entity_id="pocp-agent-forge-0", limit=5)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].id, entry.id)

    def test_evolve_capability(self):
        evolve_capability(
            self.db,
            "pocp-agent-vault-0",
            "wallet_reconciliation_v2",
            source="test",
        )
        self.db.commit()
        caps = get_agent_capabilities(self.db, "pocp-agent-vault-0")
        self.assertIn("wallet_reconciliation_v2", caps["evolved_capabilities"])

    def test_handoff_ingest_memory(self):
        h = create_handoff(
            self.db,
            from_agent_entity_id=NEXUS_ID,
            to_agent_entity_id="pocp-agent-gauge-0",
            scope="Run pytest for studio",
        )
        complete_handoff(self.db, h.id, status="completed")
        with unittest.mock.patch.dict(os.environ, {"POCP_STUDIO_AUTO_EVOLVE": "true"}):
            ingest_handoff_memory(self.db, h)
        self.db.commit()
        rows = list_memories(self.db, agent_entity_id="pocp-agent-gauge-0", limit=5)
        self.assertGreaterEqual(len(rows), 1)

    def test_vault_summary(self):
        append_memory(
            self.db,
            agent_entity_id="pocp-agent-atlas-0",
            title="Schema note",
            content="v0.3 entity schema",
            sync_file=False,
        )
        self.db.commit()
        vault = vault_summary(self.db)
        self.assertIn("total_entries", vault)
        self.assertGreaterEqual(vault["total_entries"], 1)

    def test_auto_evolution_tick_runs(self):
        with unittest.mock.patch.dict(os.environ, {"POCP_STUDIO_AUTO_EVOLVE": "true"}):
            result = run_auto_evolution_tick(self.db)
        self.assertTrue(result.get("ran"))


if __name__ == "__main__":
    unittest.main()
