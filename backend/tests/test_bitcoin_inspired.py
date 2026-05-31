"""Tests for Bitcoin-inspired Merkle inclusion and wallet transaction replay."""

import unittest
from datetime import datetime

from services.ledger_chain import compute_record_hash
from services.ledger_merkle import (
    build_inclusion_bundle,
    build_merkle_inclusion_proof,
    merkle_root,
    verify_merkle_inclusion,
)
from services.wallet_audit import compute_balances_from_transactions, verify_wallet_export


class LedgerMerkleTests(unittest.TestCase):
    def test_inclusion_proof_roundtrip(self):
        hashes = [f"hash{i:02d}" for i in range(4)]
        root = merkle_root(hashes)
        for idx, leaf in enumerate(hashes):
            proof = build_merkle_inclusion_proof(hashes, idx)
            self.assertTrue(verify_merkle_inclusion(leaf, proof, root))

    def test_inclusion_bundle(self):
        t0 = datetime(2026, 1, 1, 12, 0, 0)
        h0 = compute_record_hash(None, "registration_grant", {"amount": 100}, t0)
        h1 = compute_record_hash(h0, "contribution_approved", {"cp": 10}, t0)
        bundle = build_inclusion_bundle([h0, h1], h1)
        self.assertIsNotNone(bundle)
        assert bundle is not None
        self.assertEqual(bundle["leaf_index"], 1)
        self.assertTrue(
            verify_merkle_inclusion(
                bundle["leaf_hash"],
                bundle["merkle_proof"],
                bundle["merkle_root"],
            )
        )


class WalletAuditTests(unittest.TestCase):
    def test_compute_balances(self):
        from models.wallet import CreditType

        txs = [
            type("T", (), {"amount": 100, "credit_type": CreditType.ai_credits})(),
            type("T", (), {"amount": -5, "credit_type": CreditType.ai_credits})(),
            type("T", (), {"amount": 20, "credit_type": CreditType.cp})(),
        ]
        balances = compute_balances_from_transactions(txs)
        self.assertEqual(balances["ai_credits"], 95.0)
        self.assertEqual(balances["cp_balance"], 20.0)

    def test_wallet_export_verify(self):
        export = {
            "wallets": [{"id": "w1", "entity_id": "e1", "cp_balance": 20, "ai_credits": 95}],
            "transactions": [
                {"wallet_id": "w1", "amount": 100, "credit_type": "ai_credits"},
                {"wallet_id": "w1", "amount": -5, "credit_type": "ai_credits"},
                {"wallet_id": "w1", "amount": 20, "credit_type": "cp"},
            ],
        }
        result = verify_wallet_export(export)
        self.assertTrue(result["valid"])

    def test_wallet_export_detects_mismatch(self):
        export = {
            "wallets": [{"id": "w1", "entity_id": "e1", "cp_balance": 999, "ai_credits": 95}],
            "transactions": [
                {"wallet_id": "w1", "amount": 20, "credit_type": "cp"},
            ],
        }
        result = verify_wallet_export(export)
        self.assertFalse(result["valid"])


if __name__ == "__main__":
    unittest.main()
