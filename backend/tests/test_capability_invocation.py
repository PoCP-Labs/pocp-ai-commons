"""PR-07 — capability-bound invocation ledger."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401
from database import Base
from genesis import DESUI_ID, LUMEN_0_ID, RAIN_ID, ensure_genesis_entities
from models.capability import CapabilityType, CapabilityUnit, EntityCapability
from models.capability_invocation import CapabilityInvocationRecord, CapabilityInvocationStatus
from models.entity import Entity, EntityStatus, EntityType
from models.wallet import CreditTransaction, CreditType, Wallet
from services.capability_invocation.store import (
    complete_capability_invocation,
    create_capability_invocation,
    invocation_ref_from_record,
    link_capability_invocation_settlement,
    record_to_dict,
    transition_capability_invocation,
)
from services.exchange_spine import emit_exchange_settled
from services.invocation_ledger import validate_invocation_ref


class CapabilityInvocationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        ensure_genesis_entities(self.db)
        self.db.add(
            EntityCapability(
                id="pocp-cap-lumen-reasoning",
                entity_id=LUMEN_0_ID,
                capability_type=CapabilityType.reasoning,
                name="Advisory reasoning",
                unit=CapabilityUnit.llm_token,
            )
        )
        self.db.add(Wallet(entity_id=RAIN_ID, ai_credits=100, cp_balance=0))
        self.db.add(Wallet(entity_id=LUMEN_0_ID, ai_credits=0, cp_balance=0))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_create_and_complete_state_machine(self):
        record = create_capability_invocation(
            self.db,
            caller_entity_id=RAIN_ID,
            callee_entity_id=LUMEN_0_ID,
            capability_id="pocp-cap-lumen-reasoning",
            input_payload={"prompt": "hello"},
            cost_unit="AIC",
            cost_amount=1.0,
        )
        self.db.commit()
        self.assertEqual(record.status, CapabilityInvocationStatus.created)

        transition_capability_invocation(self.db, record.id, status="running")
        complete_capability_invocation(
            self.db, record.id, output_payload={"response": "ok"}
        )
        self.db.commit()
        updated = self.db.get(CapabilityInvocationRecord, record.id)
        self.assertEqual(updated.status, CapabilityInvocationStatus.completed)
        self.assertTrue(updated.output_hash.startswith("sha256:"))

    def test_invocation_ref_links_caller_callee_capability(self):
        record = create_capability_invocation(
            self.db,
            caller_entity_id=RAIN_ID,
            callee_entity_id=LUMEN_0_ID,
            capability_id="pocp-cap-lumen-reasoning",
            input_hash="sha256:abc",
        )
        complete_capability_invocation(self.db, record.id, output_hash="sha256:def")
        link_capability_invocation_settlement(self.db, record.id, exchange_id="ex_test001")
        ref = invocation_ref_from_record(record)
        check = validate_invocation_ref(
            {
                **ref,
                "receipt_hash": ref.get("receipt_hash") or "sha256:def",
                "settlement_ref": "ex_test001",
                "status": "settled",
            }
        )
        self.assertTrue(check["valid"], check)
        self.assertEqual(ref["source_entity_id"], RAIN_ID)
        self.assertEqual(ref["target_entity_id"], LUMEN_0_ID)
        self.assertEqual(ref["capability_id"], "pocp-cap-lumen-reasoning")

    def test_emit_exchange_settled_links_capability_invocation(self):
        record = create_capability_invocation(
            self.db,
            caller_entity_id=RAIN_ID,
            callee_entity_id=LUMEN_0_ID,
            capability_id="pocp-cap-lumen-reasoning",
            input_hash="sha256:in",
        )
        complete_capability_invocation(self.db, record.id, output_hash="sha256:out")
        self.db.flush()

        consumer = self.db.query(Wallet).filter(Wallet.entity_id == RAIN_ID).one()
        provider = self.db.query(Wallet).filter(Wallet.entity_id == LUMEN_0_ID).one()
        debit = CreditTransaction(
            wallet_id=consumer.id,
            amount=-2,
            credit_type=CreditType.ai_credits,
            reason="cap_invoke",
        )
        credit = CreditTransaction(
            wallet_id=provider.id,
            amount=2,
            credit_type=CreditType.ai_credits,
            reason="cap_provide",
        )
        self.db.add_all([debit, credit])
        self.db.flush()

        ledger = emit_exchange_settled(
            self.db,
            consumer_entity_id=RAIN_ID,
            provider_entity_ids=[LUMEN_0_ID],
            exchange_kind="capability",
            credit_transactions=[debit, credit],
            capability_id="pocp-cap-lumen-reasoning",
            capability_invocation_id=record.id,
            receipt_hash="sha256:out",
        )
        self.db.commit()

        updated = self.db.get(CapabilityInvocationRecord, record.id)
        self.assertEqual(updated.status, CapabilityInvocationStatus.settled)
        self.assertTrue(updated.exchange_id)
        inv_ref = (ledger.payload or {}).get("invocation_ref") or {}
        self.assertEqual(inv_ref.get("capability_id"), "pocp-cap-lumen-reasoning")
        self.assertEqual(inv_ref.get("settlement_ref"), updated.exchange_id)

    def test_record_to_dict_legacy_shape(self):
        record = create_capability_invocation(
            self.db,
            caller_entity_id=RAIN_ID,
            callee_entity_id=DESUI_ID,
            capability_id="pocp-cap-lumen-reasoning",
            input_hash="sha256:x",
        )
        payload = record_to_dict(record)
        self.assertIn("caller_entity_id", payload)
        self.assertIn("callee_entity_id", payload)
        self.assertEqual(payload["caller_entity_id"], RAIN_ID)


if __name__ == "__main__":
    unittest.main()
