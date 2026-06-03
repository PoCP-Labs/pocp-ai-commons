"""Wallet audit — transaction replay and GET /wallets/audit contract."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.wallet import CreditTransaction, CreditType, Wallet
from services.compute_receipt import build_compute_receipt
from services.compute_settlement import settle_bilateral
from services.wallet_audit import audit_all_wallets, audit_wallet_by_entity


class WalletAuditServiceTests(unittest.TestCase):
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
        consumer = Wallet(entity_id="human-1", cp_balance=0, ai_credits=100)
        provider = Wallet(entity_id="llm-1", cp_balance=0, ai_credits=0)
        self.db.add(consumer)
        self.db.add(provider)
        self.db.flush()
        self.db.add(
            CreditTransaction(
                wallet_id=consumer.id,
                amount=100,
                credit_type=CreditType.ai_credits,
                reason="Registration grant",
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_audit_all_wallets_contract_fields(self):
        result = audit_all_wallets(self.db)
        self.assertIn("valid", result)
        self.assertIn("wallet_count", result)
        self.assertIn("invalid_count", result)
        self.assertIn("wallets", result)
        self.assertEqual(result.get("audit_model"), "transaction_replay_v0.1")
        self.assertTrue(result["valid"])
        self.assertEqual(result["wallet_count"], 2)
        self.assertEqual(result["invalid_count"], 0)

    def test_audit_valid_after_exchange_settlement(self):
        receipt = build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="node-a",
            capability="llm_inference",
            adapter="mock",
            initiator_entity_id="human-1",
            extra={
                "usage": {
                    "metering_mode": "token",
                    "prompt_tokens": 40,
                    "completion_tokens": 20,
                    "total_tokens": 60,
                }
            },
        )
        settle_bilateral(self.db, receipt, consumer_entity_id="human-1")
        self.db.commit()

        audit = audit_all_wallets(self.db)
        self.assertTrue(audit["valid"], audit)
        for row in audit["wallets"]:
            self.assertIn("entity_id", row)
            self.assertIn("stored", row)
            self.assertIn("computed_from_transactions", row)
            self.assertIn("transaction_count", row)

    def test_audit_wallet_by_entity_detects_silent_mint(self):
        wallet = self.db.query(Wallet).filter(Wallet.entity_id == "human-1").one()
        wallet.ai_credits = 999
        self.db.commit()

        row = audit_wallet_by_entity(self.db, "human-1")
        assert row is not None
        self.assertFalse(row["valid"])
        self.assertIsNotNone(row.get("mismatch"))


if __name__ == "__main__":
    unittest.main()
