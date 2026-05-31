"""Bilateral settlement — consumer debit + provider credit + intel provider."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.capability import (
    CapabilityAvailability,
    CapabilityType,
    CapabilityUnit,
    EntityCapability,
    PriceModel,
)
from models.entity import Entity, EntityStatus, EntityType
from models.wallet import CreditTransaction, CreditType, Wallet
from services.compute_receipt import build_compute_receipt
from services.compute_settlement import settle_bilateral, settle_intel_provider
from services.market_pricing import register_market_profile


class BilateralSettlementTests(unittest.TestCase):
    def setUp(self):
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
        self.db.add(Wallet(entity_id="human-1", cp_balance=0, ai_credits=100))
        self.db.add(Wallet(entity_id="llm-1", cp_balance=0, ai_credits=10))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_bilateral_debits_consumer_and_credits_provider(self):
        receipt = build_compute_receipt(
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
        consumer_before = self.db.query(Wallet).filter(Wallet.entity_id == "human-1").one().ai_credits
        provider_before = self.db.query(Wallet).filter(Wallet.entity_id == "llm-1").one().ai_credits

        result = settle_bilateral(self.db, receipt, consumer_entity_id="human-1")
        self.db.commit()
        self.assertTrue(result["settled"])
        self.assertTrue(result["consumer_debited"])
        self.assertGreater(result["consumer_tokens"], 0)
        self.assertGreater(result["credits_granted"], 0)

        consumer_after = self.db.query(Wallet).filter(Wallet.entity_id == "human-1").one().ai_credits
        provider_after = self.db.query(Wallet).filter(Wallet.entity_id == "llm-1").one().ai_credits
        self.assertLess(consumer_after, consumer_before)
        self.assertGreater(provider_after, provider_before)

        debits = (
            self.db.query(CreditTransaction)
            .filter(CreditTransaction.amount < 0)
            .all()
        )
        credits = (
            self.db.query(CreditTransaction)
            .filter(CreditTransaction.amount > 0)
            .all()
        )
        self.assertEqual(len(debits), 1)
        self.assertEqual(len(credits), 1)

    def test_bilateral_idempotent(self):
        receipt = build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="node-a",
            capability="witness",
            adapter="mock",
            contribution_id="c1",
            initiator_entity_id="human-1",
            extra={"usage": {"metering_mode": "intel", "service": "witness"}},
        )
        first = settle_bilateral(self.db, receipt, consumer_entity_id="human-1")
        self.db.commit()
        second = settle_bilateral(self.db, receipt, consumer_entity_id="human-1")
        self.assertTrue(first["settled"])
        self.assertFalse(second["settled"])

    def test_insufficient_consumer_balance(self):
        poor = Wallet(entity_id="human-1", cp_balance=0, ai_credits=0)
        self.db.query(Wallet).filter(Wallet.entity_id == "human-1").delete()
        self.db.add(poor)
        self.db.commit()
        receipt = build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="node-a",
            capability="llm_inference",
            adapter="mock",
            initiator_entity_id="human-1",
            extra={
                "usage": {
                    "metering_mode": "token",
                    "prompt_tokens": 5000,
                    "completion_tokens": 5000,
                    "total_tokens": 10000,
                }
            },
        )
        result = settle_bilateral(self.db, receipt, consumer_entity_id="human-1")
        self.assertFalse(result["settled"])
        self.assertEqual(result["reason"], "insufficient_consumer_balance")

    def test_market_profile_override(self):
        entity = self.db.get(Entity, "llm-1")
        register_market_profile(
            self.db,
            "llm-1",
            {
                "overrides": {
                    "llm_inference:qwen2.5:7b": {"provider_per_1k_total": 2.0, "consumer_per_1k_prompt": 3.0}
                }
            },
        )
        self.db.commit()
        receipt = build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="node-a",
            capability="llm_inference",
            model="qwen2.5:7b",
            adapter="ollama",
            initiator_entity_id="human-1",
            extra={
                "usage": {
                    "metering_mode": "token",
                    "prompt_tokens": 1000,
                    "completion_tokens": 0,
                    "total_tokens": 1000,
                }
            },
        )
        result = settle_bilateral(self.db, receipt, consumer_entity_id="human-1")
        self.db.commit()
        self.assertTrue(result["settled"])
        self.assertGreaterEqual(result["credits_granted"], 2.0)
        self.assertGreaterEqual(result["consumer_tokens"], 3.0)


class IntelSettlementTests(unittest.TestCase):
    def setUp(self):
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
                id="skill-1",
                entity_type=EntityType.skill,
                name="Code Review",
                status=EntityStatus.active,
            )
        )
        self.db.add(Wallet(entity_id="human-1", cp_balance=0, ai_credits=50))
        self.db.add(Wallet(entity_id="skill-1", cp_balance=0, ai_credits=0))
        self.db.add(
            EntityCapability(
                entity_id="skill-1",
                capability_type=CapabilityType.coding,
                name="Code Review Skill",
                unit=CapabilityUnit.skill_invocation,
                price_model=PriceModel.fixed,
                base_price=8.0,
                accepted_units=["AIC"],
                verification_method="human_review",
                availability=CapabilityAvailability.available,
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_intel_settlement_uses_registry_price(self):
        result = settle_intel_provider(
            self.db,
            provider_entity_id="skill-1",
            service="skill_invocation",
            consumer_entity_id="human-1",
            contribution_id="c1",
        )
        self.db.commit()
        self.assertTrue(result["settled"])
        self.assertEqual(result["credits_granted"], 8.0)
        self.assertEqual(result["consumer_tokens"], 8.0)
        skill_wallet = self.db.query(Wallet).filter(Wallet.entity_id == "skill-1").one()
        self.assertEqual(skill_wallet.ai_credits, 8.0)


if __name__ == "__main__":
    unittest.main()
