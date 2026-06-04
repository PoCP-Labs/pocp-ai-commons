"""CIP-P4.3 federation reputation read indexer stub tests (Sentinel-0)."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.ledger import LedgerRecord
from models.wallet import CreditTransaction, CreditType, Wallet
from services.anti_abuse import (
    FEDERATION_REPUTATION_READ_SCHEMA,
    FederationReputationReadIndexer,
    exchange_settled_reputation_fields,
    reputation_scope_from_exchange_payload,
)
from services.exchange_spine import emit_exchange_settled


class FederationReputationStubTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        for entity_id, entity_type in (
            ("human-1", EntityType.human),
            ("skill-1", EntityType.skill),
            ("peer-skill-1", EntityType.skill),
        ):
            self.db.add(
                Entity(
                    id=entity_id,
                    entity_type=entity_type,
                    name=entity_id,
                    status=EntityStatus.active,
                )
            )
        self.db.add(Wallet(entity_id="human-1", ai_credits=100, cp_balance=0))
        self.db.add(Wallet(entity_id="skill-1", ai_credits=0, cp_balance=0))
        self.db.commit()
        self.consumer_wallet = self.db.query(Wallet).filter(Wallet.entity_id == "human-1").one()
        self.provider_wallet = self.db.query(Wallet).filter(Wallet.entity_id == "skill-1").one()

    def tearDown(self):
        self.db.close()

    def _emit_exchange(
        self,
        *,
        consumer: str = "human-1",
        provider: str = "skill-1",
        capability: str = "code_review",
        extra_payload: dict | None = None,
    ) -> LedgerRecord:
        debit = CreditTransaction(
            wallet_id=self.consumer_wallet.id,
            amount=-2,
            credit_type=CreditType.ai_credits,
            reason="capability_consumed:test",
        )
        credit = CreditTransaction(
            wallet_id=self.provider_wallet.id,
            amount=1,
            credit_type=CreditType.ai_credits,
            reason="capability_provided:test",
        )
        self.db.add(debit)
        self.db.add(credit)
        self.db.flush()
        return emit_exchange_settled(
            self.db,
            consumer_entity_id=consumer,
            provider_entity_ids=[provider],
            exchange_kind="capability",
            credit_transactions=[debit, credit],
            capability=capability,
            extra_payload=extra_payload,
        )

    def test_scope_from_exchange_payload(self):
        scope = reputation_scope_from_exchange_payload(
            {"capability": "gpu_inference", "exchange_kind": "compute"},
        )
        self.assertEqual(scope, "gpu_inference")

    def test_exchange_settled_fields_require_verified_parties(self):
        fields = exchange_settled_reputation_fields(
            {
                "exchange_id": "ex_1",
                "consumer_entity_id": "human-1",
                "provider_entity_ids": ["skill-1"],
                "capability": "code_review",
            },
        )
        self.assertIsNotNone(fields)
        assert fields is not None
        self.assertEqual(fields["subject_entity_id"], "skill-1")
        self.assertEqual(fields["actor_entity_id"], "human-1")
        self.assertEqual(fields["source_ref"], "ex_1")
        self.assertEqual(fields["delta"], "success")

    def test_self_feedback_exchange_skipped(self):
        skipped = exchange_settled_reputation_fields(
            {
                "exchange_id": "ex_self",
                "consumer_entity_id": "skill-1",
                "provider_entity_ids": ["skill-1"],
                "capability": "code_review",
            },
        )
        self.assertIsNone(skipped)

    def test_index_from_db_builds_read_model(self):
        self._emit_exchange(capability="code_review")
        self._emit_exchange(
            capability="gpu_inference",
            extra_payload={"peer_route": True, "peer_node_id": "peer-node-a"},
        )
        self.db.commit()

        indexer = FederationReputationReadIndexer()
        indexer.index_from_db(self.db)
        model = indexer.read_model()

        self.assertEqual(model["schema_version"], FEDERATION_REPUTATION_READ_SCHEMA)
        self.assertEqual(model["indexed_exchange_count"], 2)
        self.assertEqual(model["peer_route_exchange_count"], 1)
        self.assertEqual(model["snapshot_count"], 2)

        review = indexer.indexer.get_snapshot("skill-1", "code_review")
        self.assertIsNotNone(review)
        assert review is not None
        self.assertEqual(review.success_count, 1)

    def test_idempotent_reindex_does_not_double_count(self):
        record = self._emit_exchange()
        self.db.commit()

        indexer = FederationReputationReadIndexer()
        indexer.index_ledger_record(record)
        indexer.index_ledger_record(record)
        snap = indexer.indexer.get_snapshot("skill-1", "code_review")
        self.assertIsNotNone(snap)
        assert snap is not None
        self.assertEqual(snap.success_count, 1)
        self.assertEqual(indexer.read_model()["indexed_exchange_count"], 1)


if __name__ == "__main__":
    unittest.main()
