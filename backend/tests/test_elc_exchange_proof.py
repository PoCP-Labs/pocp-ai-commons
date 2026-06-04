"""ELC, exchange proof, and federation exchange import tests."""

import json
import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.federation import FederatedImport
from models.wallet import CreditTransaction, CreditType, Wallet
from services.compute_receipt import build_compute_receipt
from services.compute_settlement import settle_bilateral
from services.entity_local_chain import build_entity_local_chain, find_exchange_ledger_record
from services.exchange_proof import build_exchange_proof_packet, verify_exchange_proof_integrity
from services.federation_exchange_import import (
    import_federated_exchange_proof,
    is_public_federation_url,
    resolve_staging_exchange_import_peers,
    staging_exchange_import_policy,
)
from services.verify_standalone import verify_proof_integrity


class ElcExchangeProofTests(unittest.TestCase):
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
        self.receipt = build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="node-a",
            capability="llm_inference",
            adapter="mock",
            initiator_entity_id="human-1",
            extra={
                "usage": {
                    "metering_mode": "token",
                    "prompt_tokens": 80,
                    "completion_tokens": 40,
                    "total_tokens": 120,
                }
            },
        )
        result = settle_bilateral(self.db, self.receipt, consumer_entity_id="human-1")
        self.db.commit()
        self.exchange_id = result["exchange_id"]

    def tearDown(self):
        self.db.close()

    def test_entity_local_chain_lists_exchange(self):
        elc = build_entity_local_chain(self.db, "human-1", limit=10)
        self.assertEqual(elc["entity_id"], "human-1")
        self.assertGreaterEqual(elc["total"], 1)
        self.assertEqual(elc["records"][-1]["ref_id"], self.exchange_id)
        self.assertIsNotNone(elc["records"][-1]["spv"])

    def test_exchange_proof_and_verify(self):
        proof = build_exchange_proof_packet(self.db, self.exchange_id)
        self.assertIsNotNone(proof)
        self.assertEqual(proof["proof_type"], "pocp_exchange_proof")
        self.assertIn("exchange_inclusion", proof)

        direct = verify_exchange_proof_integrity(proof)
        self.assertTrue(direct["valid"], direct)

        routed = verify_proof_integrity(proof)
        self.assertTrue(routed["valid"], routed)

    def test_get_exchange_by_id(self):
        record = find_exchange_ledger_record(self.db, self.exchange_id)
        self.assertIsNotNone(record)
        self.assertEqual((record.payload or {}).get("exchange_id"), self.exchange_id)

    def test_federation_l1_import_exchange_proof(self):
        proof = build_exchange_proof_packet(self.db, self.exchange_id)
        with patch.dict(os.environ, {"POCP_ALLOW_UNTRUSTED_IMPORT": "true"}):
            record = import_federated_exchange_proof(
                self.db,
                "peer-node-a",
                proof,
                acceptance_level="L1",
            )
            self.db.commit()
            self.assertEqual(record.contribution_type, "exchange")
            self.assertEqual(record.payload.get("import_kind"), "exchange_proof")

            again = import_federated_exchange_proof(
                self.db,
                "peer-node-a",
                proof,
                acceptance_level="L1",
            )
            self.assertEqual(again.id, record.id)

        count = self.db.query(FederatedImport).count()
        self.assertEqual(count, 1)

    def test_staging_exchange_import_peer_resolution(self):
        trusted_json = json.dumps(
            [
                {
                    "node_id": "peer-a",
                    "base_url": "https://api-a.staging.example",
                    "trust_weight": 0.5,
                },
                {
                    "node_id": "peer-b",
                    "base_url": "https://api-b.staging.example",
                    "trust_weight": 0.5,
                },
            ]
        )
        with patch.dict(
            os.environ,
            {
                "POCP_TRUSTED_NODES": trusted_json,
                "POCP_STAGING_FEDERATION_NODE_A": "",
                "POCP_STAGING_FEDERATION_NODE_B": "",
            },
            clear=False,
        ):
            from services.trust_config import clear_trusted_nodes_cache

            clear_trusted_nodes_cache()
            node_a, node_b, source_id, importer_id = resolve_staging_exchange_import_peers()
            self.assertEqual(node_a, "https://api-a.staging.example")
            self.assertEqual(node_b, "https://api-b.staging.example")
            self.assertEqual(source_id, "peer-a")
            self.assertEqual(importer_id, "peer-b")
            policy = staging_exchange_import_policy()
            self.assertEqual(policy["trusted_peer_count"], 2)
            self.assertEqual(len(policy["public_peer_urls"]), 2)
            clear_trusted_nodes_cache()

    def test_is_public_federation_url(self):
        self.assertTrue(is_public_federation_url("https://api.staging.example"))
        self.assertFalse(is_public_federation_url("http://127.0.0.1:8100"))


if __name__ == "__main__":
    unittest.main()
