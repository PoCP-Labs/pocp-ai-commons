"""Federation cross-node PoCP Token settlement tests — v0.4."""

import os
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.federation import FederationSettlement
from models.wallet import CreditTransaction, Wallet
from services.compute_receipt import build_compute_receipt
from services.federation_community import local_federation_entity_id
from services.federation_settlement import (
    apply_settlement_intent,
    build_settlement_intent,
    is_federation_peer_execution,
    settle_compute_receipt,
    settle_federation_cross_node,
)


def _peer_receipt(**kwargs):
    extra = kwargs.pop("extra", {})
    extra.setdefault("source", "peer_node")
    extra.setdefault("base_url", "http://peer-b:8101")
    return build_compute_receipt(
        provider_entity_id=kwargs.pop("provider_entity_id", None),
        provider_node_id=kwargs.pop("provider_node_id", "node-b"),
        capability=kwargs.pop("capability", "llm_inference"),
        adapter=kwargs.pop("adapter", "mock"),
        contribution_id=kwargs.pop("contribution_id", "c-fed-1"),
        initiator_entity_id=kwargs.pop("initiator_entity_id", "human-1"),
        extra={
            "usage": {
                "metering_mode": "token",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "estimated": True,
            },
            **extra,
        },
        **kwargs,
    )


class FederationSettlementTests(unittest.TestCase):
    def setUp(self):
        self._prev_node = os.environ.get("POCP_NODE_ID")
        self._prev_priv = os.environ.get("POCP_NODE_PRIVATE_KEY")
        self._prev_pub = os.environ.get("POCP_NODE_PUBLIC_KEY")
        os.environ["POCP_NODE_ID"] = "node-a"

        private = Ed25519PrivateKey.generate()
        self.private_hex = private.private_bytes_raw().hex()
        self.public_hex = private.public_key().public_bytes_raw().hex()
        os.environ["POCP_NODE_PRIVATE_KEY"] = self.private_hex
        os.environ["POCP_NODE_PUBLIC_KEY"] = self.public_hex

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
                id=local_federation_entity_id(),
                entity_type=EntityType.community,
                name="Local Federation",
                status=EntityStatus.active,
            )
        )
        self.db.add(Wallet(entity_id="human-1", cp_balance=0, ai_credits=100))
        self.db.add(
            Wallet(entity_id=local_federation_entity_id(), cp_balance=0, ai_credits=0)
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        if self._prev_node is None:
            os.environ.pop("POCP_NODE_ID", None)
        else:
            os.environ["POCP_NODE_ID"] = self._prev_node
        if self._prev_priv is None:
            os.environ.pop("POCP_NODE_PRIVATE_KEY", None)
        else:
            os.environ["POCP_NODE_PRIVATE_KEY"] = self._prev_priv
        if self._prev_pub is None:
            os.environ.pop("POCP_NODE_PUBLIC_KEY", None)
        else:
            os.environ["POCP_NODE_PUBLIC_KEY"] = self._prev_pub

    def test_is_federation_peer_execution(self):
        receipt = _peer_receipt()
        self.assertTrue(is_federation_peer_execution(receipt))
        local = build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="node-a",
            capability="llm_inference",
            extra={"source": "local_node"},
        )
        self.assertFalse(is_federation_peer_execution(local))

    def test_consumer_debits_without_local_provider_credit(self):
        receipt = _peer_receipt()
        selected = {
            "source": "peer_node",
            "provider_node_id": "node-b",
            "base_url": "http://peer-b:8101",
        }
        consumer_before = self.db.query(Wallet).filter(Wallet.entity_id == "human-1").one().ai_credits

        result = settle_federation_cross_node(
            self.db,
            receipt,
            consumer_entity_id="human-1",
            selected_provider=selected,
            push_intent=False,
        )
        self.db.commit()

        self.assertTrue(result["settled"])
        self.assertTrue(result["federation"])
        self.assertTrue(result["consumer_debited"])
        self.assertGreater(result["consumer_tokens"], 0)

        consumer_after = self.db.query(Wallet).filter(Wallet.entity_id == "human-1").one().ai_credits
        self.assertLess(consumer_after, consumer_before)

        credits = self.db.query(CreditTransaction).filter(CreditTransaction.amount > 0).all()
        self.assertEqual(len(credits), 0)

        record = self.db.query(FederationSettlement).one()
        self.assertEqual(record.side, "consumer")
        self.assertEqual(record.status, "consumer_debited")
        self.assertEqual(record.provider_node_id, "node-b")

    def test_provider_mirror_credits_local_federation_wallet(self):
        os.environ["POCP_NODE_ID"] = "node-b"
        receipt = _peer_receipt(provider_node_id="node-b")
        intent = build_settlement_intent(
            receipt=receipt,
            consumer_node_id="node-a",
            provider_node_id="node-b",
            consumer_entity_id="human-1",
            consumer_tokens=5.0,
            provider_tokens=3.0,
        )

        result = apply_settlement_intent(self.db, intent)
        self.db.commit()

        self.assertTrue(result["settled"])
        self.assertEqual(result["status"], "provider_credited")
        self.assertEqual(result["provider_entity_id"], local_federation_entity_id())

        wallet = self.db.query(Wallet).filter(Wallet.entity_id == local_federation_entity_id()).one()
        self.assertEqual(wallet.ai_credits, 3.0)

        provider_record = (
            self.db.query(FederationSettlement)
            .filter(FederationSettlement.side == "provider")
            .one()
        )
        self.assertEqual(provider_record.status, "provider_credited")

    def test_cross_node_idempotent(self):
        receipt = _peer_receipt()
        first = settle_federation_cross_node(
            self.db,
            receipt,
            consumer_entity_id="human-1",
            push_intent=False,
        )
        self.db.commit()
        second = settle_federation_cross_node(
            self.db,
            receipt,
            consumer_entity_id="human-1",
            push_intent=False,
        )
        self.assertTrue(first["settled"])
        self.assertFalse(second["settled"])
        self.assertEqual(second["reason"], "already_settled")

    def test_settle_compute_receipt_routes_peer_to_federation(self):
        receipt = _peer_receipt()
        with patch(
            "services.federation_settlement.settle_federation_cross_node",
            return_value={"settled": True, "federation": True},
        ) as mock_fed:
            result = settle_compute_receipt(
                self.db,
                receipt,
                consumer_entity_id="human-1",
                selected_provider={"source": "peer_node"},
            )
        self.assertTrue(result["federation"])
        mock_fed.assert_called_once()

    def test_settle_compute_receipt_routes_local_to_bilateral(self):
        receipt = build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="node-a",
            capability="llm_inference",
            initiator_entity_id="human-1",
            extra={"source": "local_node", "usage": {"metering_mode": "intel", "service": "witness"}},
        )
        self.db.add(
            Entity(
                id="llm-1",
                entity_type=EntityType.llm,
                name="Provider",
                status=EntityStatus.active,
            )
        )
        self.db.add(Wallet(entity_id="llm-1", cp_balance=0, ai_credits=0))
        self.db.commit()

        with patch("services.compute_settlement.settle_bilateral", return_value={"settled": True}) as mock_bi:
            result = settle_compute_receipt(self.db, receipt, consumer_entity_id="human-1")
        self.assertTrue(result["settled"])
        mock_bi.assert_called_once()


if __name__ == "__main__":
    unittest.main()
