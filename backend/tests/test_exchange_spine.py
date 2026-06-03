"""Exchange spine — unified exchange_settled events."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.ledger import LedgerRecord
from models.wallet import CreditTransaction, CreditType, Wallet
from services.exchange_spine import emit_exchange_settled, infer_exchange_kind, new_exchange_id


class ExchangeSpineTests(unittest.TestCase):
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
        self.db.add(Wallet(entity_id="human-1", ai_credits=100, cp_balance=0))
        self.db.add(Wallet(entity_id="llm-1", ai_credits=0, cp_balance=0))
        self.db.commit()
        self.consumer_wallet = self.db.query(Wallet).filter(Wallet.entity_id == "human-1").one()
        self.provider_wallet = self.db.query(Wallet).filter(Wallet.entity_id == "llm-1").one()

    def tearDown(self):
        self.db.close()

    def test_new_exchange_id_prefix(self):
        self.assertTrue(new_exchange_id().startswith("ex_"))

    def test_infer_exchange_kind(self):
        self.assertEqual(infer_exchange_kind(capability="gpu_inference"), "compute")
        self.assertEqual(infer_exchange_kind(capability="coding"), "capability")
        self.assertEqual(
            infer_exchange_kind(receipt={"capability": "llm_inference"}, skill_entity_id="skill-1"),
            "hybrid",
        )

    def test_emit_exchange_settled_links_transactions(self):
        debit = CreditTransaction(
            wallet_id=self.consumer_wallet.id,
            amount=-5,
            credit_type=CreditType.ai_credits,
            reason="compute_consumed:abc",
        )
        credit = CreditTransaction(
            wallet_id=self.provider_wallet.id,
            amount=3,
            credit_type=CreditType.ai_credits,
            reason="compute_provided:abc",
        )
        self.db.add(debit)
        self.db.add(credit)
        self.db.flush()

        record = emit_exchange_settled(
            self.db,
            consumer_entity_id="human-1",
            provider_entity_ids=["llm-1"],
            exchange_kind="compute",
            credit_transactions=[debit, credit],
            receipt_hash="sha256:abc",
            capability="gpu_inference",
            usage={"gpu_seconds": 10},
            legacy_event_type="compute_settlement",
        )
        self.db.commit()

        self.assertEqual(record.event_type, "exchange_settled")
        payload = record.payload or {}
        self.assertEqual(payload.get("exchange_kind"), "compute")
        self.assertEqual(payload.get("legacy_event_type"), "compute_settlement")
        self.assertIn(debit.id, payload.get("credit_transaction_ids") or [])
        self.assertIn(credit.id, payload.get("credit_transaction_ids") or [])
        self.assertEqual(debit.ledger_record_id, record.id)
        self.assertEqual(credit.ledger_record_id, record.id)
        ref = payload.get("invocation_ref") or {}
        self.assertTrue(ref.get("invocation_id"))
        self.assertEqual(ref.get("settlement_ref"), payload.get("exchange_id"))
        self.assertTrue(payload.get("invocation_chain_digest"))

        rows = self.db.query(LedgerRecord).filter(LedgerRecord.event_type == "exchange_settled").all()
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
