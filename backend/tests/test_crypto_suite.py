import os
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from services.crypto_suite import (
    SUITE_V01_CLASSIC,
    SUITE_V02_HYBRID,
    build_signature_block,
    crypto_readiness_report,
    hash_digest,
    suite_meets_minimum,
    verify_federation_signatures,
)


class CryptoSuiteTests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        self.public_hex = self.private.public_key().public_bytes_raw().hex()
        self.pqc_private = os.urandom(32).hex()
        self.pqc_public = hash_digest(self.pqc_private, "sha256")

    def test_suite_minimum_ordering(self):
        self.assertTrue(suite_meets_minimum(SUITE_V02_HYBRID, SUITE_V01_CLASSIC))
        self.assertFalse(suite_meets_minimum(SUITE_V01_CLASSIC, SUITE_V02_HYBRID))

    def test_hash_digest_sha256(self):
        self.assertEqual(len(hash_digest("hello")), 64)

    @patch.dict(
        os.environ,
        {
            "POCP_NODE_PRIVATE_KEY": Ed25519PrivateKey.generate().private_bytes_raw().hex(),
            "POCP_CRYPTO_SUITE": SUITE_V01_CLASSIC,
        },
        clear=False,
    )
    def test_classic_signature_block(self):
        block = build_signature_block("message-1", node_id="node-test", signed_field="test.field")
        self.assertIsNotNone(block)
        self.assertEqual(block["crypto_suite"], SUITE_V01_CLASSIC)
        self.assertIn("classic", block["signatures"])
        verify_federation_signatures(block, "message-1")

    @patch.dict(
        os.environ,
        {
            "POCP_NODE_PRIVATE_KEY": Ed25519PrivateKey.generate().private_bytes_raw().hex(),
            "POCP_NODE_PQC_PRIVATE_KEY": os.urandom(32).hex(),
            "POCP_CRYPTO_SUITE": SUITE_V02_HYBRID,
        },
        clear=False,
    )
    def test_hybrid_signature_block(self):
        block = build_signature_block("message-2", node_id="node-hybrid", signed_field="test.field")
        self.assertIsNotNone(block)
        self.assertEqual(block["crypto_suite"], SUITE_V02_HYBRID)
        self.assertIn("pqc", block["signatures"])
        verify_federation_signatures(block, "message-2")

    def test_readiness_report_shape(self):
        report = crypto_readiness_report()
        self.assertIn("quantum_readiness", report)
        self.assertIn("available_suites", report)
        self.assertEqual(report["pqc_production_target"], "ml-dsa-65")


if __name__ == "__main__":
    unittest.main()
