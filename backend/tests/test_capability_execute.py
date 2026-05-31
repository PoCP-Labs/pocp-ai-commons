"""Tests for direct Skill and Agent execution."""

import asyncio
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from genesis import LUMEN_0_ID
from models.entity import Entity, EntityStatus, EntityType
from models.skill import Skill
from models.wallet import Wallet
from services.capability_execute import execute_agent, execute_skill
from services.capability_import import import_skill_from_skill_md

SAMPLE_SKILL = """---
name: exec-test
description: Execution test skill.
---

# Exec Test

Return a structured answer.
"""


class CapabilityExecuteTests(unittest.TestCase):
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
        self.agent = Entity(
            entity_type=EntityType.agent,
            name="HelperAgent",
            description="Generic helper",
            status=EntityStatus.active,
            metadata_={"capabilities": ["exec-test"]},
        )
        self.db.add_all([self.human, self.llm, self.agent])
        self.db.flush()
        self.db.add(Wallet(entity_id=self.human.id, ai_credits=100, cp_balance=0))
        self.db.commit()

        imported = import_skill_from_skill_md(
            self.db,
            source="pocp_native",
            skill_md=SAMPLE_SKILL,
            maintainer_id=self.human.id,
            activate=True,
        )
        self.skill_entity_id = imported["entity_id"]
        skill_entity = self.db.get(Entity, self.skill_entity_id)
        skill_entity.name = "exec-test"
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_execute_skill_native(self):
        result = asyncio.run(
            execute_skill(
                self.db,
                human_entity_id=self.human.id,
                skill_entity_id=self.skill_entity_id,
                user_input="Explain matrix multiplication in R.",
                llm_provider="mock",
            )
        )
        self.assertEqual(result["execution_type"], "skill")
        self.assertEqual(result["mode"], "native")
        self.assertTrue(result["trace_id"])
        self.assertIn("output", result)
        self.assertGreater(result["billing"]["credits_spent"], 0)

        wallet = self.db.query(Wallet).filter(Wallet.entity_id == self.human.id).first()
        self.assertLess(wallet.ai_credits, 100)

    def test_execute_agent_generic(self):
        from models.agent import Agent

        self.db.add(Agent(entity_id=self.agent.id, config={"capabilities": ["exec-test"]}, maintainer_id=self.human.id))
        self.db.commit()

        result = asyncio.run(
            execute_agent(
                self.db,
                human_entity_id=self.human.id,
                agent_entity_id=self.agent.id,
                user_input="Summarize eigenvalues.",
                skill_entity_id=self.skill_entity_id,
                llm_provider="mock",
            )
        )
        self.assertEqual(result["execution_type"], "agent")
        self.assertEqual(result["agent_entity_id"], self.agent.id)
        self.assertTrue(result["trace_id"])

    def test_pending_skill_rejected(self):
        skill_entity = self.db.get(Entity, self.skill_entity_id)
        skill_entity.status = EntityStatus.pending
        self.db.commit()

        with self.assertRaises(Exception) as ctx:
            asyncio.run(
                execute_skill(
                    self.db,
                    human_entity_id=self.human.id,
                    skill_entity_id=self.skill_entity_id,
                    user_input="test",
                    llm_provider="mock",
                )
            )
        self.assertIn("active", str(ctx.exception.detail).lower())


if __name__ == "__main__":
    unittest.main()
