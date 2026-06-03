"""Tests for dialogue invoke → capability_execute with CapabilityReceipt (PL-2)."""

import asyncio
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from genesis import LUMEN_0_ID
from models.entity import Entity, EntityStatus, EntityType
from models.invocation import InvocationStep
from models.wallet import Wallet
from services.capability.dialogue_invoke import execute_metered_dialogue_invoke
from services.capability_import import import_skill_from_skill_md
from services.capability_receipt import CAPABILITY_RECEIPT_SCHEMA

SAMPLE_SKILL = """---
name: dlg-meter
description: Dialogue metered invoke test.
---

# Test

Answer briefly.
"""


class CapabilityDialogueInvokeTests(unittest.TestCase):
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
        self.db.add_all([self.human, self.llm])
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
        self.skill = self.db.get(Entity, imported["entity_id"])
        self.skill.name = "dlg-meter"
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_metered_dialogue_invoke_attaches_capability_receipts(self):
        result = asyncio.run(
            execute_metered_dialogue_invoke(
                self.db,
                source=self.human,
                target=self.skill,
                payload={"input": "What is PoCP?", "llm_provider": "mock"},
                refs_in={},
                dialogue_id="dlg_pl2_1",
            )
        )
        self.assertTrue(result.get("trace_id"))
        self.assertIn("capability_receipts", result)
        self.assertGreater(len(result["capability_receipts"]), 0)
        self.assertEqual(result["capability_receipts"][0]["schema"], CAPABILITY_RECEIPT_SCHEMA)
        self.assertIn("receipt", result)
        self.assertIn("capability_receipts", result["receipt"])

        steps = (
            self.db.query(InvocationStep)
            .filter(InvocationStep.trace_id == result["trace_id"])
            .order_by(InvocationStep.step_order)
            .all()
        )
        self.assertEqual(steps[0].metadata_.get("dialogue_id"), "dlg_pl2_1")
        self.assertEqual(steps[0].metadata_.get("dialogue_kind"), "invoke")
        self.assertIn("capability_receipt", steps[0].metadata_)


if __name__ == "__main__":
    unittest.main()
