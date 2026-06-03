"""PR-A — invocation ledger normalization and exchange integrity chain."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.invocation import InvocationStatus, InvocationStep, InvocationTrace
from models.ledger import LedgerRecord
from models.wallet import CreditTransaction, CreditType, Wallet
from services.ai_chat import chat_and_burn_credits
from services.compute_receipt import build_compute_receipt
from services.compute_settlement import settle_bilateral
from services.exchange_proof import build_exchange_proof_packet, verify_exchange_proof_integrity
from services.exchange_spine import emit_exchange_settled
from services.invocation_ledger import (
    build_invocation_ref,
    compute_invocation_chain_digest,
    validate_invocation_ref,
    verify_exchange_invocation_chain,
)


class InvocationLedgerNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
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

    def test_build_invocation_ref_required_fields(self):
        ref = build_invocation_ref(
            source_entity_id="human-1",
            target_entity_id="llm-1",
            receipt_hash="sha256:abc",
            settlement_ref="ex_test123",
        )
        check = validate_invocation_ref(ref)
        self.assertTrue(check["valid"], check)

    def test_emit_exchange_settled_includes_invocation_ref(self):
        consumer = self.db.query(Wallet).filter(Wallet.entity_id == "human-1").one()
        provider = self.db.query(Wallet).filter(Wallet.entity_id == "llm-1").one()
        debit = CreditTransaction(
            wallet_id=consumer.id,
            amount=-5,
            credit_type=CreditType.ai_credits,
            reason="compute_consumed:abc",
        )
        credit = CreditTransaction(
            wallet_id=provider.id,
            amount=3,
            credit_type=CreditType.ai_credits,
            reason="compute_provided:abc",
        )
        self.db.add_all([debit, credit])
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
        )
        self.db.commit()

        payload = record.payload or {}
        ref = payload.get("invocation_ref") or {}
        self.assertTrue(validate_invocation_ref(ref)["valid"], ref)
        self.assertEqual(ref.get("settlement_ref"), payload.get("exchange_id"))
        self.assertEqual(ref.get("receipt_hash"), "sha256:abc")
        self.assertTrue(payload.get("invocation_chain_digest"))

    def test_compute_settlement_links_trace_id(self):
        trace = InvocationTrace(
            initiator_id="human-1",
            status=InvocationStatus.completed,
        )
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
                    "prompt_tokens": 50,
                    "completion_tokens": 25,
                    "total_tokens": 75,
                },
            },
        )
        result = settle_bilateral(self.db, receipt, consumer_entity_id="human-1")
        self.db.commit()

        record = (
            self.db.query(LedgerRecord)
            .filter(LedgerRecord.event_type == "exchange_settled")
            .one()
        )
        payload = record.payload or {}
        ref = payload.get("invocation_ref") or {}
        self.assertEqual(ref.get("trace_id"), trace.id)
        self.assertEqual(payload.get("invocation_trace_id"), trace.id)
        self.assertTrue(payload.get("invocation_chain_digest"))

        integrity = verify_exchange_invocation_chain(self.db, result["exchange_id"])
        self.assertTrue(integrity["valid"], integrity)
        self.assertTrue(integrity["invocation_chain_digest"])

    def test_exchange_proof_includes_chain_digest(self):
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
        result = settle_bilateral(self.db, receipt, consumer_entity_id="human-1")
        self.db.commit()

        proof = build_exchange_proof_packet(self.db, result["exchange_id"])
        self.assertIsNotNone(proof)
        assert proof is not None
        self.assertIn("invocation_ref", proof)
        self.assertTrue(proof.get("invocation_chain_digest"))
        verified = verify_exchange_proof_integrity(proof)
        self.assertTrue(verified["valid"], verified)

    def test_chain_digest_stable_for_same_steps(self):
        steps = [
            {"step_order": 1, "source_entity_id": "h", "target_entity_id": "a", "action": "uses"},
            {"step_order": 2, "source_entity_id": "a", "target_entity_id": "l", "action": "invokes_llm"},
        ]
        d1 = compute_invocation_chain_digest(steps)
        d2 = compute_invocation_chain_digest(list(reversed(steps)))
        self.assertEqual(d1, d2)

    def test_ai_chat_exchange_integrity(self):
        import asyncio

        async def _run():
            return await chat_and_burn_credits(
                self.db,
                entity_id="human-1",
                message="invocation ledger test",
                provider="mock",
            )

        result = asyncio.run(_run())
        self.db.commit()
        exchange_id = result.get("exchange_id")
        self.assertTrue(exchange_id)
        integrity = verify_exchange_invocation_chain(self.db, exchange_id)
        self.assertTrue(integrity["valid"], integrity)


class ExchangeIntegrityRouteTests(unittest.TestCase):
    """GET /api/v1/exchanges/{exchange_id}/integrity — PA-2 route contract."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
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
        self.exchange_id = result["exchange_id"]

        from database import get_db
        from fastapi.testclient import TestClient
        from main import app

        request_session = sessionmaker(bind=self.engine)

        def _override_get_db():
            db = request_session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = _override_get_db
        self.client = TestClient(app)
        self.app = app

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_integrity_route_returns_valid(self):
        resp = self.client.get(f"/api/v1/exchanges/{self.exchange_id}/integrity")
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertTrue(data.get("valid"), data)
        self.assertEqual(data.get("exchange_id"), self.exchange_id)
        self.assertTrue(data.get("invocation_chain_digest"))

    def test_integrity_route_404_unknown_exchange(self):
        resp = self.client.get("/api/v1/exchanges/ex_nonexistent000/integrity")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
