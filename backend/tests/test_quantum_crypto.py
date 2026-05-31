"""Quantum crypto agility — hybrid signatures and hash-algorithm ledger rows."""

import os
import unittest
from datetime import datetime

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from services.crypto_suite import (
    SUITE_V02_HYBRID,
    SUITE_V03_HASH,
    active_hash_algorithm,
    build_signature_block,
    hash_digest,
    suite_spec,
    verify_federation_signatures,
)
from services.ledger_chain import compute_record_hash, verify_ledger_records
from services.pqc_dsa import sign_pqc, verify_pqc


class HashAgilityTests(unittest.TestCase):
    def test_sha256_and_sha3_differ(self):
        msg = "pocp-ledger-material"
        self.assertNotEqual(hash_digest(msg, "sha256"), hash_digest(msg, "sha3-256"))

    def test_compute_record_hash_respects_algorithm(self):
        t0 = datetime(2026, 1, 1, 12, 0, 0)
        h256 = compute_record_hash(None, "registration_grant", {"n": 1}, t0, hash_algorithm="sha256")
        h3 = compute_record_hash(None, "registration_grant", {"n": 1}, t0, hash_algorithm="sha3-256")
        self.assertNotEqual(h256, h3)

    def test_mixed_algorithm_chain_verifies(self):
        t0 = datetime(2026, 1, 1, 12, 0, 0)
        t1 = datetime(2026, 1, 1, 12, 1, 0)
        h0 = compute_record_hash(None, "genesis", {}, t0, hash_algorithm="sha256")
        h1 = compute_record_hash(h0, "approved", {"cp": 10}, t1, hash_algorithm="sha3-256")
        result = verify_ledger_records(
            [
                {
                    "id": "1",
                    "event_type": "genesis",
                    "payload": {},
                    "prev_hash": None,
                    "record_hash": h0,
                    "hash_algorithm": "sha256",
                    "created_at": t0,
                },
                {
                    "id": "2",
                    "event_type": "approved",
                    "payload": {"cp": 10},
                    "prev_hash": h0,
                    "record_hash": h1,
                    "hash_algorithm": "sha3-256",
                    "created_at": t1,
                },
            ]
        )
        self.assertTrue(result["valid"])


class HybridSignatureTests(unittest.TestCase):
    def setUp(self):
        self._env = {
            k: os.environ.get(k)
            for k in (
                "POCP_CRYPTO_SUITE",
                "POCP_NODE_PRIVATE_KEY",
                "POCP_NODE_PUBLIC_KEY",
                "POCP_NODE_PQC_PRIVATE_KEY",
                "POCP_NODE_PQC_PUBLIC_KEY",
            )
        }
        private = Ed25519PrivateKey.generate()
        os.environ["POCP_CRYPTO_SUITE"] = SUITE_V02_HYBRID
        os.environ["POCP_NODE_PRIVATE_KEY"] = private.private_bytes_raw().hex()
        os.environ["POCP_NODE_PUBLIC_KEY"] = private.public_key().public_bytes_raw().hex()
        os.environ["POCP_NODE_PQC_PRIVATE_KEY"] = "50f1aad1c21870d89b32c33b75ad7666c313aca0ae8b20486ca5240a563de7c8"
        os.environ["POCP_NODE_PQC_PUBLIC_KEY"] = "26c3ea06eae3d672175add0f824e90f8ac3a5238f8ae44dced71130bfec21c21"

    def tearDown(self):
        for key, value in self._env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_hybrid_signature_block_has_pqc_leg(self):
        block = build_signature_block("anchor-root", signed_field="merkle_root")
        assert block is not None
        self.assertEqual(block["crypto_suite"], SUITE_V02_HYBRID)
        self.assertIn("pqc", block["signatures"])

    def test_verify_hybrid_signatures(self):
        message = "proof-hash-deadbeef"
        block = build_signature_block(message, signed_field="integrity.proof_hash")
        assert block is not None
        verify_federation_signatures(block, message)

    def test_pqc_stub_roundtrip(self):
        message = "test-pqc-message"
        result = sign_pqc(message)
        assert result is not None
        algorithm, pub, sig = result
        self.assertTrue(verify_pqc(message, algorithm, pub, sig))


class SuiteRegistryTests(unittest.TestCase):
    def test_v03_hash_suite_uses_sha3(self):
        spec = suite_spec(SUITE_V03_HASH)
        self.assertEqual(spec["hash_algorithm"], "sha3-256")

    def test_active_hash_follows_suite_env(self):
        prev = os.environ.get("POCP_CRYPTO_SUITE")
        os.environ["POCP_CRYPTO_SUITE"] = SUITE_V03_HASH
        os.environ["POCP_NODE_PQC_PRIVATE_KEY"] = "50f1aad1c21870d89b32c33b75ad7666c313aca0ae8b20486ca5240a563de7c8"
        try:
            self.assertEqual(active_hash_algorithm(), "sha3-256")
        finally:
            if prev is None:
                os.environ.pop("POCP_CRYPTO_SUITE", None)
            else:
                os.environ["POCP_CRYPTO_SUITE"] = prev


class LiboqsOptionalTests(unittest.TestCase):
    def test_liboqs_mldsa_roundtrip_when_installed(self):
        from services.pqc_dsa import PQC_SIG_TARGET, liboqs_available, verify_pqc

        if not liboqs_available():
            self.skipTest("liboqs-python not installed")
        import oqs

        mech = oqs.get_enabled_sig_mechanisms()
        name = "ML-DSA-65" if "ML-DSA-65" in mech else None
        if not name:
            self.skipTest("ML-DSA-65 not in liboqs build")
        message = "pocp-test-ml-dsa"
        with oqs.Signature(name) as signer:
            signer.generate_keypair()
            signature = signer.sign(message.encode("utf-8")).hex()
            public_key = signer.export_public_key().hex()
        self.assertTrue(verify_pqc(message, PQC_SIG_TARGET, public_key, signature))


if __name__ == "__main__":
    unittest.main()
