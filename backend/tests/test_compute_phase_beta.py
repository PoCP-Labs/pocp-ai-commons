"""Phase β — compute attribution, settlement, liveness."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.invocation import InvocationStatus, InvocationStep, InvocationTrace
from models.wallet import CreditType, Wallet
from services.compute_attribution import build_compute_attribution_block
from services.compute_jobs import clear_job_store, create_job_record
from services.compute_profile import is_profile_stale, refresh_provider_liveness
from services.compute_receipt import build_compute_receipt, verify_compute_receipt
from services.compute_settlement import settle_compute_provider
from tests.compute_test_db import make_compute_test_session


class ComputeAttributionTests(unittest.TestCase):
    def test_build_block_from_trace_and_jobs(self):
        db = make_compute_test_session()
        clear_job_store(db)
        try:
            receipt = build_compute_receipt(
                provider_entity_id="llm-1",
                provider_node_id="node-a",
                capability="llm_inference",
                adapter="mock",
                contribution_id="contrib-1",
                input_material="hello",
                output_material="world",
            )
            trace = InvocationTrace(
                id="trace-1",
                initiator_id="human-1",
                contribution_id="contrib-1",
                model_provider="mock",
                status=InvocationStatus.completed,
            )
            step = InvocationStep(
                trace_id="trace-1",
                step_order=1,
                source_entity_id="skill-1",
                target_entity_id="llm-1",
                action="invokes_llm",
                metadata_={"compute_receipt": receipt},
            )
            trace.steps = [step]
            create_job_record(
                db,
                capability="witness",
                initiator_entity_id="human-1",
                contribution_id="contrib-1",
                task_id=None,
                constraints={},
                selected_provider={"provider_entity_id": "llm-2"},
                receipt=receipt,
                status="completed",
            )
            db.commit()
            block = build_compute_attribution_block(db, "contrib-1", [trace])
            self.assertEqual(block["contribution_id"], "contrib-1")
            self.assertGreaterEqual(block["receipt_count"], 1)
            self.assertEqual(block["verified_count"], block["receipt_count"])
        finally:
            db.close()


class ComputeSettlementTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        provider = Entity(
            id="llm-1",
            entity_type=EntityType.llm,
            name="Lumen-0",
            status=EntityStatus.active,
        )
        self.db.add(provider)
        self.db.add(
            Entity(
                id="human-1",
                entity_type=EntityType.human,
                name="Consumer",
                status=EntityStatus.active,
            )
        )
        self.db.add(Wallet(entity_id="llm-1", cp_balance=0, ai_credits=10))
        self.db.add(Wallet(entity_id="human-1", cp_balance=0, ai_credits=100))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_settle_idempotent(self):
        receipt = build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="node-a",
            capability="llm_inference",
            adapter="mock",
            contribution_id="c1",
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
        first = settle_compute_provider(self.db, receipt, consumer_entity_id="human-1")
        self.db.commit()
        self.assertTrue(first["settled"])
        self.assertGreater(first["credits_granted"], 0)

        second = settle_compute_provider(self.db, receipt, consumer_entity_id="human-1")
        self.assertFalse(second["settled"])


class ComputeLivenessTests(unittest.TestCase):
    def test_is_profile_stale(self):
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        self.assertTrue(is_profile_stale({"last_heartbeat": old}, stale_seconds=900))
        fresh = datetime.now(timezone.utc).isoformat()
        self.assertFalse(is_profile_stale({"last_heartbeat": fresh}, stale_seconds=900))

    def test_refresh_marks_offline(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine)()
        entity = Entity(
            entity_type=EntityType.llm,
            name="Stale Node",
            status=EntityStatus.active,
            metadata_={
                "compute_profile": {
                    "spec_version": "0.1",
                    "status": "active",
                    "last_heartbeat": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
                    "offers": [{"capability": "witness"}],
                    "endpoints": {},
                    "capacity": {},
                    "accountability": {},
                    "policy": {},
                }
            },
        )
        db.add(entity)
        db.flush()
        updated = refresh_provider_liveness(db, stale_seconds=900)
        self.assertEqual(updated, 1)
        self.assertEqual(entity.metadata_["compute_profile"]["status"], "offline")


if __name__ == "__main__":
    unittest.main()
