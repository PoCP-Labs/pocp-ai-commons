"""PR-B — settlement policy versioning and offline replay."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.ledger import LedgerRecord
from models.wallet import CreditTransaction, CreditType, Wallet
from services.compute_receipt import build_compute_receipt
from services.compute_settlement import settle_bilateral
from services.settlement_policy import (
    get_settlement_policy,
    policy_tag,
    replay_bilateral_quote,
    replay_flat_debit_quote,
)


class SettlementPolicyReplayTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add_all(
            [
                Entity(
                    id="human-1",
                    entity_type=EntityType.human,
                    name="Consumer",
                    status=EntityStatus.active,
                ),
                Entity(
                    id="llm-1",
                    entity_type=EntityType.llm,
                    name="Provider",
                    status=EntityStatus.active,
                ),
            ]
        )
        self.db.add(Wallet(entity_id="human-1", ai_credits=100, cp_balance=0))
        self.db.add(Wallet(entity_id="llm-1", ai_credits=0, cp_balance=0))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_policy_tag_has_hash(self):
        tag = policy_tag("compute_settlement.v1")
        self.assertEqual(tag["settlement_policy_id"], "compute_settlement.v1")
        self.assertTrue(tag["policy_hash"])
        self.assertEqual(tag["settlement_policy_version"], "1.0.0")

    def test_get_settlement_policy(self):
        policy = get_settlement_policy("ai_chat.v1")
        self.assertIsNotNone(policy)
        assert policy is not None
        self.assertEqual(policy.get("kind"), "flat_debit")

    def test_replay_matches_settlement(self):
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
        quote = replay_bilateral_quote(receipt, db=self.db)
        self.assertTrue(quote["valid"])

        result = settle_bilateral(self.db, receipt, consumer_entity_id="human-1")
        self.db.commit()

        consumer_tx = (
            self.db.query(CreditTransaction)
            .filter(CreditTransaction.amount < 0)
            .order_by(CreditTransaction.id.desc())
            .first()
        )
        provider_tx = (
            self.db.query(CreditTransaction)
            .filter(CreditTransaction.amount > 0)
            .order_by(CreditTransaction.id.desc())
            .first()
        )
        self.assertIsNotNone(consumer_tx)
        self.assertIsNotNone(provider_tx)
        assert consumer_tx is not None and provider_tx is not None
        self.assertEqual(abs(float(consumer_tx.amount)), quote["consumer_amount"])
        self.assertEqual(float(provider_tx.amount), quote["provider_amount"])

        record = (
            self.db.query(LedgerRecord)
            .filter(LedgerRecord.event_type == "exchange_settled")
            .one()
        )
        payload = record.payload or {}
        self.assertEqual(payload.get("settlement_policy_id"), "compute_settlement.v1")
        self.assertTrue(payload.get("policy_hash"))
        self.assertEqual(result["exchange_id"], payload.get("exchange_id"))

    def test_flat_debit_replay(self):
        quote = replay_flat_debit_quote(policy_id="ai_chat.v1")
        self.assertTrue(quote["valid"])
        self.assertEqual(quote["consumer_amount"], quote["provider_amount"])


if __name__ == "__main__":
    unittest.main()
