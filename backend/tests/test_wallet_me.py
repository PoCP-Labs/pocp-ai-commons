"""Tests for wallet /me service and API helpers."""

import unittest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.wallet import CreditTransaction, CreditType, Wallet
from services.rights import issue_registration_bc
from services.wallet_service import list_wallet_transactions, quote_spend, wallet_summary


class WalletServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.entity = Entity(
            entity_type=EntityType.human,
            name="Wallet User",
            status=EntityStatus.active,
        )
        self.db.add(self.entity)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_summary_after_registration_grant(self):
        issue_registration_bc(self.db, self.entity)
        self.db.commit()
        summary = wallet_summary(self.db, self.entity.id)
        self.assertGreater(summary["ai_credits"], 0)
        self.assertTrue(summary["audit_valid"])
        self.assertFalse(summary["rights_policy"]["cp"]["spendable"])
        self.assertTrue(summary["rights_policy"]["bc"]["spendable"])

    def test_transactions_include_balance_after(self):
        wallet = Wallet(entity_id=self.entity.id, ai_credits=100, cp_balance=0)
        self.db.add(wallet)
        self.db.flush()
        t0 = datetime.utcnow()
        self.db.add(
            CreditTransaction(
                wallet_id=wallet.id,
                amount=100,
                credit_type=CreditType.ai_credits,
                reason="Registration grant",
                created_at=t0,
            )
        )
        self.db.add(
            CreditTransaction(
                wallet_id=wallet.id,
                amount=-5,
                credit_type=CreditType.ai_credits,
                reason="AI chat",
                created_at=t0 + timedelta(seconds=1),
            )
        )
        self.db.commit()
        result = list_wallet_transactions(self.db, self.entity.id, limit=10)
        self.assertEqual(result["total"], 2)
        latest = result["items"][0]
        self.assertEqual(latest["amount"], -5)
        self.assertEqual(latest["balance_after"]["ai_credits"], 95.0)

    def test_transactions_credit_type_filter(self):
        wallet = Wallet(entity_id=self.entity.id, ai_credits=50, cp_balance=10)
        self.db.add(wallet)
        self.db.flush()
        self.db.add_all(
            [
                CreditTransaction(
                    wallet_id=wallet.id,
                    amount=50,
                    credit_type=CreditType.ai_credits,
                    reason="grant",
                ),
                CreditTransaction(
                    wallet_id=wallet.id,
                    amount=10,
                    credit_type=CreditType.cp,
                    reason="proof",
                ),
            ]
        )
        self.db.commit()
        result = list_wallet_transactions(
            self.db, self.entity.id, credit_type=CreditType.cp
        )
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["credit_type"], "cp")

    def test_quote_ai_chat_allowed(self):
        wallet = Wallet(entity_id=self.entity.id, ai_credits=100, cp_balance=0)
        self.db.add(wallet)
        self.db.commit()
        quote = quote_spend(self.db, self.entity.id, "ai_chat")
        self.assertEqual(quote["action"], "ai_chat")
        self.assertTrue(quote["allowed"])
        self.assertEqual(quote["cost"], 5.0)
        self.assertEqual(quote["balance_after"], 95.0)

    def test_quote_ai_chat_insufficient(self):
        wallet = Wallet(entity_id=self.entity.id, ai_credits=2, cp_balance=0)
        self.db.add(wallet)
        self.db.commit()
        quote = quote_spend(self.db, self.entity.id, "ai_chat")
        self.assertFalse(quote["allowed"])

    def test_entity_summary_public(self):
        wallet = Wallet(entity_id=self.entity.id, ai_credits=50, cp_balance=5)
        self.db.add(wallet)
        self.db.flush()
        self.db.add(
            CreditTransaction(
                wallet_id=wallet.id,
                amount=50,
                credit_type=CreditType.ai_credits,
                reason="Registration grant",
            )
        )
        self.db.commit()
        summary = wallet_summary(self.db, self.entity.id)
        self.assertEqual(summary["ai_credits"], 50.0)
        self.assertEqual(summary["cp_balance"], 5.0)

    def test_entity_transactions_pagination(self):
        wallet = Wallet(entity_id=self.entity.id, ai_credits=0, cp_balance=0)
        self.db.add(wallet)
        self.db.flush()
        for i in range(3):
            self.db.add(
                CreditTransaction(
                    wallet_id=wallet.id,
                    amount=float(i + 1),
                    credit_type=CreditType.ai_credits,
                    reason=f"grant-{i}",
                )
            )
        self.db.commit()
        page = list_wallet_transactions(self.db, self.entity.id, limit=2, offset=0)
        self.assertEqual(page["total"], 3)
        self.assertEqual(len(page["items"]), 2)


if __name__ == "__main__":
    unittest.main()
