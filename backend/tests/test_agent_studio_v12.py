"""Agent Studio v1.2 — graph edges and patch suggestions."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.agent import Agent
from services.agent_studio.evolution import apply_proposal, review_proposal
from services.agent_studio.graph_edges import append_meta_agent_studio_graph_edges
from services.agent_studio.handoffs import create_handoff
from services.agent_studio.missions import create_mission
from services.agent_studio.outcomes import record_outcome
from services.agent_studio.evolution import process_outcome
from services.graph import build_contribution_graph
from services.meta_agent_registry import ensure_meta_agents


class AgentStudioV12Tests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        ensure_meta_agents(self.db)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_graph_includes_studio_edges(self):
        create_handoff(
            self.db,
            from_agent_entity_id="pocp-agent-forge-0",
            to_agent_entity_id="pocp-agent-nexus-0",
            scope="test handoff",
        )
        self.db.commit()
        graph = build_contribution_graph(self.db)
        studio_edges = [e for e in graph["edges"] if e.get("connection_layer") == "studio"]
        self.assertGreater(len(studio_edges), 0)
        self.assertIn("studio", graph["edge_layer_counts"])
        self.assertGreater(graph["edge_layer_counts"]["studio"], 0)
        self.assertGreaterEqual(graph.get("meta_agent_nodes", 0), 15)

    def test_apply_writes_patch_file(self):
        outcome = record_outcome(
            self.db,
            agent_entity_id="pocp-agent-gauge-0",
            kind="test",
            result="fail",
            summary="ci red",
        )
        proposal = process_outcome(self.db, outcome.id)
        self.assertIsNotNone(proposal)
        review_proposal(
            self.db,
            proposal.id,
            approve=True,
            reviewer_entity_id="pocp-agent-atlas-0",
        )
        result = apply_proposal(
            self.db, proposal.id, actor_entity_id="pocp-agent-nexus-0"
        )
        self.assertIn("patch_suggestion", result)
        self.assertTrue(result["patch_suggestion"]["patch_file"].startswith("agents/patches/"))
        agent = self.db.query(Agent).filter(Agent.entity_id == "pocp-agent-gauge-0").first()
        self.assertIn("last_patch_file", agent.config.get("learning_profile", {}))


if __name__ == "__main__":
    unittest.main()
