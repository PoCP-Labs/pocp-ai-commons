"""Tests for wallet ledger linking and export bundle."""

import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.ledger import LedgerRecord
from models.wallet import CreditTransaction, CreditType, Wallet
from services.wallet_ledger_link import batch_ledger_links, transaction_category
from services.wallet_service import export_wallet_bundle


class WalletLedgerLinkTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.entity = Entity(
            entity_type=EntityType.human,
            name="Link User",
            status=EntityStatus.active,
        )
        self.db.add(self.entity)
        self.db.commit()
        self.wallet = Wallet(entity_id=self.entity.id, ai_credits=95, cp_balance=0)
        self.db.add(self.wallet)
        self.db.flush()

    def tearDown(self):
        self.db.close()

    def test_transaction_category_compute(self):
        self.assertEqual(transaction_category("compute_consumed:abc", -10), "compute_spend")
        self.assertEqual(transaction_category("compute_provider:abc", 10), "compute_earn")

    def test_links_ai_chat_burn(self):
        now = datetime.utcnow()
        tx = CreditTransaction(
            wallet_id=self.wallet.id,
            amount=-5,
            credit_type=CreditType.ai_credits,
            reason="AI chat usage",
            created_at=now,
        )
        self.db.add(tx)
        self.db.flush()
        ledger = LedgerRecord(
            event_type="ai_credits_burned",
            payload={
                "entity_id": self.entity.id,
                "wallet_id": self.wallet.id,
                "credits_spent": 5,
                "remaining_credits": 95,
            },
            created_at=now,
        )
        self.db.add(ledger)
        self.db.commit()

        links = batch_ledger_links(self.db, self.wallet, [tx])
        self.assertIn(tx.id, links)
        self.assertEqual(links[tx.id]["ledger_event_type"], "ai_credits_burned")

    def test_export_wallet_bundle(self):
        self.wallet.ai_credits = 100
        self.db.add(
            CreditTransaction(
                wallet_id=self.wallet.id,
                amount=100,
                credit_type=CreditType.ai_credits,
                reason="Registration grant",
            )
        )
        self.db.commit()
        bundle = export_wallet_bundle(self.db, self.entity.id)
        self.assertEqual(bundle["export_kind"], "wallet_entity_v0.1")
        self.assertEqual(bundle["entity_id"], self.entity.id)
        self.assertIn("audit", bundle)
        self.assertGreaterEqual(len(bundle["transactions"]), 1)
        from services.wallet_service import verify_entity_wallet_export

        verified = verify_entity_wallet_export(bundle)
        self.assertTrue(verified["valid"])


if __name__ == "__main__":
    unittest.main()
