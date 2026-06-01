"""Tests for Entity connection matrix and instance API."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from intelligence.entity_ontology import (
    connection_matrix_document,
    invocation_action_for,
    ontology_document,
    validate_invocation_edge,
)
from models.contribution import (
    ContributionEvent,
    ContributionParticipant,
    ContributionStatus,
    ParticipantRole,
)
from models.entity import Entity, EntityStatus, EntityType
from models.invocation import InvocationStatus, InvocationStep, InvocationTrace
from models.task import Task, TaskStatus
from services.entity_connections import build_entity_connections, entity_connection_matrix
from services.entity_register import register_tool


class EntityConnectionTests(unittest.TestCase):
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
        self.db.add(self.human)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_connection_matrix_has_three_layers(self):
        doc = connection_matrix_document()
        self.assertEqual(doc["spec_version"], "0.1")
        self.assertEqual(len(doc["layers"]), 3)
        self.assertIn("human", doc["entity_connection_specs"])
        self.assertIn("compute_node", doc["entity_connection_specs"])
        self.assertTrue(len(doc["invocation_edge_matrix"]) >= 10)

    def test_invocation_action_for_human_agent(self):
        self.assertEqual(invocation_action_for("human", "agent"), "uses")
        self.assertEqual(invocation_action_for("agent", "skill"), "calls")
        self.assertIsNone(invocation_action_for("dataset", "llm"))

    def test_validate_invocation_edge_strict(self):
        ok = validate_invocation_edge("human", "agent", "uses")
        self.assertTrue(ok["ok"])
        with self.assertRaises(ValueError):
            validate_invocation_edge("human", "agent", "calls", strict=True)

    def test_ontology_document_links_connections(self):
        doc = ontology_document()
        self.assertIn("entity_connections", doc)
        self.assertEqual(doc["entity_connections"]["layer_count"], 3)

    def test_build_entity_connections_structural(self):
        tool = register_tool(
            self.db,
            name="Git MCP",
            description="Git",
            maintainer_id=self.human.id,
        )
        self.db.commit()

        payload = build_entity_connections(self.db, self.human.id)
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["entity_type"], "human")
        self.assertEqual(payload["structural"]["owned_count"], 1)
        self.assertEqual(payload["structural"]["owned"][0]["entity_id"], tool.id)
        self.assertIn("agent", payload["allowed"]["can_own_types"])

    def test_build_entity_connections_protocol_and_operational(self):
        agent = Entity(
            entity_type=EntityType.agent,
            name="Clarion",
            owner_id=self.human.id,
            status=EntityStatus.active,
        )
        skill = Entity(
            entity_type=EntityType.skill,
            name="Study Skill",
            owner_id=self.human.id,
            status=EntityStatus.active,
        )
        llm = Entity(
            entity_type=EntityType.llm,
            name="Lumen",
            owner_id=self.human.id,
            status=EntityStatus.active,
        )
        self.db.add_all([agent, skill, llm])
        self.db.flush()

        task = Task(title="Study R", sponsor_id=self.human.id, status=TaskStatus.open)
        self.db.add(task)
        self.db.flush()

        contrib = ContributionEvent(
            task_id=task.id,
            primary_entity_id=self.human.id,
            contribution_type="study_notes",
            description="R notes",
            status=ContributionStatus.submitted,
        )
        self.db.add(contrib)
        self.db.flush()
        self.db.add(
            ContributionParticipant(
                contribution_id=contrib.id,
                entity_id=agent.id,
                role=ParticipantRole.executor,
                weight=0.4,
            )
        )

        trace = InvocationTrace(
            initiator_id=self.human.id,
            contribution_id=contrib.id,
            status=InvocationStatus.completed,
        )
        self.db.add(trace)
        self.db.flush()
        self.db.add_all(
            [
                InvocationStep(
                    trace_id=trace.id,
                    step_order=1,
                    source_entity_id=self.human.id,
                    target_entity_id=agent.id,
                    action="uses",
                ),
                InvocationStep(
                    trace_id=trace.id,
                    step_order=2,
                    source_entity_id=agent.id,
                    target_entity_id=skill.id,
                    action="calls",
                    metadata_={"capability_receipt": {"schema": "pocp.capability_receipt.v0.1"}},
                ),
                InvocationStep(
                    trace_id=trace.id,
                    step_order=3,
                    source_entity_id=skill.id,
                    target_entity_id=llm.id,
                    action="invokes_llm",
                ),
            ]
        )
        self.db.commit()

        agent_view = build_entity_connections(self.db, agent.id)
        assert agent_view is not None
        self.assertEqual(agent_view["protocol"]["participation_count"], 1)
        self.assertIn("executor", agent_view["protocol"]["roles_seen"])
        self.assertEqual(agent_view["operational"]["outbound_step_count"], 1)
        self.assertEqual(agent_view["operational"]["inbound_step_count"], 1)
        self.assertTrue(agent_view["operational"]["outbound_steps"][0]["has_capability_receipt"])

    def test_build_entity_connections_missing_entity(self):
        self.assertIsNone(build_entity_connections(self.db, "missing-id"))

    def test_entity_connection_matrix_alias(self):
        self.assertEqual(
            entity_connection_matrix()["docs"],
            connection_matrix_document()["docs"],
        )


if __name__ == "__main__":
    unittest.main()
