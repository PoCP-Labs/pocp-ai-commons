"""Skill orchestration multi-party split settlement — v0.4."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.wallet import CreditTransaction, Wallet
from services.compute_metering import orchestration_split_shares
from services.compute_receipt import build_compute_receipt
from services.compute_settlement import settle_bilateral
from services.entity_register import register_protocol_treasury
from services.protocol_config import get_rewards_config


class OrchestrationSplitSharesTests(unittest.TestCase):
    def setUp(self):
        get_rewards_config.cache_clear()

    def test_shares_sum_to_consumer_total(self):
        shares = orchestration_split_shares(10.0, 0.45)
        total_out = (
            shares["compute_share"]
            + shares["skill_share"]
            + shares["protocol_fee"]
            + shares["burn"]
        )
        self.assertEqual(total_out, shares["consumer_total"])
        self.assertEqual(shares["skill_share"], 1.0)
        self.assertEqual(shares["protocol_fee"], 0.5)
        self.assertEqual(shares["compute_share"], 0.45)

    def test_compute_share_capped_when_insufficient_room(self):
        shares = orchestration_split_shares(1.0, 0.9)
        self.assertEqual(shares["skill_share"], 0.1)
        self.assertEqual(shares["protocol_fee"], 0.05)
        self.assertLessEqual(shares["compute_share"], 0.85)


class SkillSplitSettlementTests(unittest.TestCase):
    def setUp(self):
        get_rewards_config.cache_clear()
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.db.add(
            Entity(
                id="human-1",
                entity_type=EntityType.human,
                name="Consumer",
                status=EntityStatus.active,
            )
        )
        self.db.add(
            Entity(
                id="llm-1",
                entity_type=EntityType.llm,
                name="Provider",
                status=EntityStatus.active,
            )
        )
        self.db.add(
            Entity(
                id="skill-1",
                entity_type=EntityType.skill,
                name="Review Skill",
                status=EntityStatus.active,
            )
        )
        treasury = register_protocol_treasury(self.db, entity_id="treasury-1")
        self.db.add(Wallet(entity_id="human-1", cp_balance=0, ai_credits=100))
        self.db.add(Wallet(entity_id="llm-1", cp_balance=0, ai_credits=0))
        self.db.add(Wallet(entity_id="skill-1", cp_balance=0, ai_credits=0))
        self.db.add(Wallet(entity_id=treasury.id, cp_balance=0, ai_credits=0))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _receipt(self) -> dict:
        return build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="node-a",
            capability="llm_inference",
            adapter="mock",
            contribution_id="c1",
            initiator_entity_id="human-1",
            input_material="hello world",
            output_material="response text here",
            extra={
                "usage": {
                    "metering_mode": "token",
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                    "estimated": True,
                }
            },
        )

    def test_split_debits_once_and_credits_all_parties(self):
        receipt = self._receipt()
        consumer_before = self.db.query(Wallet).filter(Wallet.entity_id == "human-1").one().ai_credits

        result = settle_bilateral(
            self.db,
            receipt,
            consumer_entity_id="human-1",
            skill_entity_id="skill-1",
        )
        self.db.commit()

        self.assertTrue(result["settled"])
        self.assertTrue(result["multiparty_split"])
        self.assertGreater(result["consumer_tokens"], 0)
        self.assertGreater(result["skill_credits_granted"], 0)
        self.assertGreater(result["protocol_fee_collected"], 0)

        consumer_after = self.db.query(Wallet).filter(Wallet.entity_id == "human-1").one().ai_credits
        llm_after = self.db.query(Wallet).filter(Wallet.entity_id == "llm-1").one().ai_credits
        skill_after = self.db.query(Wallet).filter(Wallet.entity_id == "skill-1").one().ai_credits
        treasury_after = self.db.query(Wallet).filter(Wallet.entity_id == "treasury-1").one().ai_credits

        self.assertAlmostEqual(consumer_before - consumer_after, result["consumer_tokens"], places=4)
        self.assertEqual(llm_after, result["credits_granted"])
        self.assertEqual(skill_after, result["skill_credits_granted"])
        self.assertEqual(treasury_after, result["protocol_fee_collected"])

        debits = self.db.query(CreditTransaction).filter(CreditTransaction.amount < 0).all()
        self.assertEqual(len(debits), 1)

        credits = self.db.query(CreditTransaction).filter(CreditTransaction.amount > 0).all()
        self.assertEqual(len(credits), 3)

        split = result["settlement"]["split"]
        self.assertEqual(split["skill_entity_id"], "skill-1")
        self.assertEqual(result["settlement"]["settlement_kind"], "skill_orchestration_split")

    def test_split_idempotent(self):
        receipt = self._receipt()
        first = settle_bilateral(
            self.db,
            receipt,
            consumer_entity_id="human-1",
            skill_entity_id="skill-1",
        )
        self.db.commit()
        second = settle_bilateral(
            self.db,
            receipt,
            consumer_entity_id="human-1",
            skill_entity_id="skill-1",
        )
        self.assertTrue(first["settled"])
        self.assertFalse(second["settled"])


if __name__ == "__main__":
    unittest.main()
