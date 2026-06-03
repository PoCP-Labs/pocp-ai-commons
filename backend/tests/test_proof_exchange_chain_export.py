"""CI-6/CI-7/CI-9 — invocation → proof → settlement chain in one export."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.invocation import InvocationStatus, InvocationStep, InvocationTrace
from models.wallet import Wallet
from services.compute_receipt import build_compute_receipt
from services.compute_settlement import settle_bilateral
from services.exchange_proof import verify_exchange_proof_integrity
from services.proof import (
    POCP_EXCHANGE_CHAIN_EXPORT_SPEC,
    POCP_EXCHANGE_CHAIN_EXPORT_TYPE,
    build_exchange_chain_export,
)


class ExchangeChainExportTests(unittest.TestCase):
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

    def test_settled_exchange_carries_chain_digest(self):
        receipt = build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="node-a",
            capability="llm_inference",
            adapter="mock",
            initiator_entity_id="human-1",
            extra={
                "usage": {
                    "metering_mode": "token",
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                }
            },
        )
        result = settle_bilateral(self.db, receipt, consumer_entity_id="human-1")
        self.db.commit()

        export = build_exchange_chain_export(self.db, result["exchange_id"])
        self.assertIsNotNone(export)
        assert export is not None
        settlement = export["settlement"]["exchange"]
        self.assertTrue(settlement.get("invocation_chain_digest"))
        self.assertEqual(
            settlement.get("invocation_chain_digest"),
            export["invocation"]["invocation_chain_digest"],
        )

    def test_chain_export_bundles_invocation_proof_settlement(self):
        trace = InvocationTrace(initiator_id="human-1", status=InvocationStatus.completed)
        self.db.add(trace)
        self.db.flush()
        self.db.add(
            InvocationStep(
                trace_id=trace.id,
                step_order=1,
                source_entity_id="human-1",
                target_entity_id="llm-1",
                action="invokes_llm",
            )
        )
        self.db.commit()

        receipt = build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="node-a",
            capability="llm_inference",
            adapter="mock",
            initiator_entity_id="human-1",
            extra={
                "trace_id": trace.id,
                "usage": {
                    "metering_mode": "token",
                    "prompt_tokens": 20,
                    "completion_tokens": 10,
                    "total_tokens": 30,
                },
            },
        )
        result = settle_bilateral(self.db, receipt, consumer_entity_id="human-1")
        self.db.commit()

        export = build_exchange_chain_export(self.db, result["exchange_id"])
        self.assertIsNotNone(export)
        assert export is not None
        self.assertEqual(export["spec_version"], POCP_EXCHANGE_CHAIN_EXPORT_SPEC)
        self.assertEqual(export["export_type"], POCP_EXCHANGE_CHAIN_EXPORT_TYPE)
        self.assertEqual(export["protocol_layers"], ["invocation", "proof", "settlement"])
        self.assertIsNotNone(export["invocation"]["trace"])
        self.assertEqual(export["invocation"]["trace"]["invocation_id"], trace.id)
        self.assertIsNotNone(export["proof"])
        self.assertEqual(export["proof"]["proof_type"], "pocp_exchange_proof")
        self.assertTrue(export["integrity"]["valid"])
        verified = verify_exchange_proof_integrity(export["proof"])
        self.assertTrue(verified["valid"], verified)


if __name__ == "__main__":
    unittest.main()
