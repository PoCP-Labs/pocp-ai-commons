"""Constitution tests — capability-first exchange spine (Art. I–II)."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.ledger import LedgerRecord
from models.wallet import CreditTransaction, CreditType, Wallet
from services.compute_receipt import build_compute_receipt
from services.compute_settlement import settle_bilateral
from services.ledger_chain import verify_ledger_chain
from services.wallet_audit import audit_all_wallets


class ConstitutionExchangeTests(unittest.TestCase):
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

    def test_c1_settlement_emits_exchange_settled_with_fk(self):
        receipt = build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="node-a",
            capability="llm_inference",
            adapter="mock",
            initiator_entity_id="human-1",
            extra={
                "usage": {
                    "metering_mode": "token",
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                }
            },
        )
        result = settle_bilateral(self.db, receipt, consumer_entity_id="human-1")
        self.db.commit()
        self.assertTrue(result["settled"])
        self.assertTrue(result.get("exchange_id"))

        exchange_rows = (
            self.db.query(LedgerRecord)
            .filter(LedgerRecord.event_type == "exchange_settled")
            .all()
        )
        self.assertEqual(len(exchange_rows), 1)
        payload = exchange_rows[0].payload or {}
        self.assertIn("exchange_id", payload)
        self.assertIn("receipt_hash", payload)

        txs = [
            tx
            for tx in self.db.query(CreditTransaction).all()
            if (tx.reason or "") != "Registration grant"
        ]
        self.assertGreaterEqual(len(txs), 2)
        for tx in txs:
            self.assertIsNotNone(tx.ledger_record_id)
            self.assertEqual(tx.ledger_record_id, exchange_rows[0].id)

    def test_c2_wallet_replay_after_exchange_settlement(self):
        receipt = build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="node-a",
            capability="llm_inference",
            adapter="mock",
            initiator_entity_id="human-1",
            extra={
                "usage": {
                    "metering_mode": "token",
                    "prompt_tokens": 50,
                    "completion_tokens": 25,
                    "total_tokens": 75,
                }
            },
        )
        settle_bilateral(self.db, receipt, consumer_entity_id="human-1")
        self.db.commit()
        self.db.refresh(self.db.query(Wallet).filter(Wallet.entity_id == "human-1").one())
        self.db.refresh(self.db.query(Wallet).filter(Wallet.entity_id == "llm-1").one())

        audit = audit_all_wallets(self.db)
        self.assertTrue(audit.get("valid"), audit)

        chain = verify_ledger_chain(self.db)
        self.assertTrue(chain.get("valid"))


if __name__ == "__main__":
    unittest.main()
