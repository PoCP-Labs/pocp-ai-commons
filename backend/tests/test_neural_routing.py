"""CI-5 — rule-based neural router resolves capabilities from public registry."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401
from database import Base
from genesis import LUMEN_0_ID
from models.capability import CapabilityType, CapabilityUnit, EntityCapability
from models.entity import Entity, EntityStatus, EntityType
from services.capability.registry import register_capability
from services.entity_register import register_compute_node
from services.neural import RuleBasedNeuralRouter, RoutingRequest, execution_plan_to_dict


class NeuralRoutingTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.human = Entity(entity_type=EntityType.human, name="Alice", status=EntityStatus.active)
        self.llm = Entity(
            id=LUMEN_0_ID,
            entity_type=EntityType.llm,
            name="Lumen-0",
            status=EntityStatus.active,
        )
        self.agent = Entity(entity_type=EntityType.agent, name="Helper", status=EntityStatus.active)
        self.db.add_all([self.human, self.llm, self.agent])
        self.db.flush()

        self.db.add(
            EntityCapability(
                id="pocp-cap-lumen-reasoning",
                entity_id=LUMEN_0_ID,
                capability_type=CapabilityType.reasoning,
                name="Advisory reasoning",
                unit=CapabilityUnit.llm_token,
            )
        )
        register_capability(
            self.db,
            entity_id=self.agent.id,
            capability_type="general",
            name="General task execution",
            unit="agent_run",
            capability_id="pocp-cap-agent-general",
        )
        register_compute_node(
            self.db,
            name="GPU-1",
            description="Local inference",
            maintainer_id=self.human.id,
            region="lab-a",
            capabilities=["gpu_inference"],
        )
        register_capability(
            self.db,
            entity_id=self.db.query(Entity).filter(Entity.entity_type == EntityType.compute_node).one().id,
            capability_type="gpu_inference",
            name="GPU inference",
            unit="gpu_second",
            capability_id="pocp-cap-gpu",
        )
        self.db.commit()
        self.router = RuleBasedNeuralRouter()

    def tearDown(self):
        self.db.close()

    def test_route_without_search_returns_plan(self):
        plan = self.router.route(
            RoutingRequest(task_id="task-1", task_type="coding", description="Review PR")
        )
        payload = execution_plan_to_dict(plan)
        self.assertEqual(payload["spec_version"], "0.3")
        self.assertGreaterEqual(len(payload["steps"]), 2)
        self.assertIsNone(payload["steps"][0]["capability_id"])

    def test_route_with_search_binds_registry_capabilities(self):
        plan = self.router.route_with_search(
            self.db,
            RoutingRequest(task_id="task-2", task_type="compute", description="Run inference"),
        )
        payload = execution_plan_to_dict(plan)
        gpu_step = payload["steps"][0]
        self.assertEqual(gpu_step["capability_type"], "gpu_inference")
        self.assertEqual(gpu_step["capability_id"], "pocp-cap-gpu")
        self.assertIsNotNone(gpu_step["entity_id"])

    def test_general_route_resolves_agent_capability(self):
        plan = self.router.route_with_search(
            self.db,
            RoutingRequest(task_id="task-3", task_type="research", description="Summarize"),
        )
        agent_step = execution_plan_to_dict(plan)["steps"][0]
        self.assertEqual(agent_step["entity_type"], "agent")
        self.assertEqual(agent_step["capability_id"], "pocp-cap-agent-general")


if __name__ == "__main__":
    unittest.main()
