"""Tests for Bitcoin-inspired standalone verification."""

import unittest
from datetime import datetime

from services.ledger_chain import append_ledger_record, compute_record_hash, verify_ledger_records
from services.ledger_merkle import merkle_root
from services.proof import compute_contribution_proof_hash
from services.verify_standalone import verify_ledger_export, verify_proof_integrity


class LedgerStandaloneVerifyTests(unittest.TestCase):
    def test_empty_chain_valid(self):
        result = verify_ledger_records([])
        self.assertTrue(result["valid"])
        self.assertEqual(result["count"], 0)

    def test_two_record_chain(self):
        t0 = datetime(2026, 1, 1, 12, 0, 0)
        t1 = datetime(2026, 1, 1, 12, 1, 0)
        h0 = compute_record_hash(None, "registration_grant", {"amount": 100}, t0)
        h1 = compute_record_hash(h0, "contribution_approved", {"cp": 20}, t1)
        records = [
            {
                "id": "r0",
                "event_type": "registration_grant",
                "payload": {"amount": 100},
                "prev_hash": None,
                "record_hash": h0,
                "created_at": t0,
            },
            {
                "id": "r1",
                "event_type": "contribution_approved",
                "payload": {"cp": 20},
                "prev_hash": h0,
                "record_hash": h1,
                "created_at": t1,
            },
        ]
        result = verify_ledger_records(records)
        self.assertTrue(result["valid"])
        self.assertEqual(result["genesis_hash"], h0)
        self.assertEqual(result["tip_hash"], h1)

    def test_tampered_record_detected(self):
        t0 = datetime(2026, 1, 1, 12, 0, 0)
        h0 = compute_record_hash(None, "registration_grant", {"amount": 100}, t0)
        records = [
            {
                "id": "r0",
                "event_type": "registration_grant",
                "payload": {"amount": 999},
                "prev_hash": None,
                "record_hash": h0,
                "created_at": t0,
            }
        ]
        result = verify_ledger_records(records)
        self.assertFalse(result["valid"])

    def test_export_bundle_merkle(self):
        t0 = datetime(2026, 1, 1, 12, 0, 0)
        h0 = compute_record_hash(None, "registration_grant", {"amount": 100}, t0)
        export = {
            "spec_version": "0.1",
            "records": [
                {
                    "id": "r0",
                    "event_type": "registration_grant",
                    "payload": {"amount": 100},
                    "prev_hash": None,
                    "record_hash": h0,
                    "created_at": t0.isoformat(),
                }
            ],
        }
        result = verify_ledger_export(export)
        self.assertTrue(result["export_valid"])
        self.assertEqual(result["merkle_root"], merkle_root([h0]))


class ProofStandaloneVerifyTests(unittest.TestCase):
    def _minimal_proof(self) -> dict:
        t0 = datetime(2026, 1, 1, 12, 0, 0)
        h0 = compute_record_hash(None, "contribution_approved", {"cp": 10}, t0)
        proof = {
            "spec_version": "0.1",
            "proof_type": "pocp_contribution_proof",
            "proof_id": "proof-test",
            "contribution_event": {"id": "contrib-1", "status": "approved"},
            "finalization": {
                "finalizer_entity_id": "pocp-entity-clarion-0",
                "mode": "witness_quorum",
                "policy_id": "entity_equal_auto_v1",
            },
            "verification": {
                "entity_finalizations": [{"approved": True, "finalizer_entity_id": "pocp-entity-clarion-0"}],
            },
            "ledger_audit": {
                "records": [
                    {
                        "id": "r0",
                        "event_type": "contribution_approved",
                        "payload": {"cp": 10},
                        "prev_hash": None,
                        "record_hash": h0,
                        "created_at": t0.isoformat(),
                    }
                ],
                "record_hashes": [h0],
            },
        }
        proof["integrity"] = {
            "ledger_tip_hash": h0,
            "hash_algorithm": "sha256",
        }
        proof["integrity"]["proof_hash"] = compute_contribution_proof_hash(proof)
        return proof

    def test_valid_minimal_proof(self):
        proof = self._minimal_proof()
        result = verify_proof_integrity(proof)
        self.assertTrue(result["valid"])
        self.assertEqual(result["contribution_id"], "contrib-1")

    def test_corrupted_proof_hash_fails(self):
        proof = self._minimal_proof()
        proof["integrity"]["proof_hash"] = "deadbeef"
        result = verify_proof_integrity(proof)
        self.assertFalse(result["valid"])


if __name__ == "__main__":
    unittest.main()
