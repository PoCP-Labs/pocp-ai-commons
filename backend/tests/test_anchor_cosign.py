"""Tests for federated Merkle anchor co-signing."""

import unittest

from services.anchor_cosign import verify_anchor_attestations
from services.federation_crypto import sign_message, verify_message


class AnchorCosignTests(unittest.TestCase):
    def test_verify_anchor_attestations_empty(self):
        result = verify_anchor_attestations({"merkle_root": "abc"})
        self.assertTrue(result["valid"])
        self.assertEqual(result["attestation_count"], 0)

    def test_verify_anchor_attestations_valid(self):
        root = "deadbeef"
        sig = sign_message(root)
        if not sig:
            self.skipTest("POCP_NODE_PRIVATE_KEY not set")
        from services.federation_crypto import get_node_public_key_hex

        pk = get_node_public_key_hex()
        self.assertTrue(pk)
        anchor = {
            "merkle_root": root,
            "peer_attestations": [
                {
                    "node_id": "peer-a",
                    "merkle_root": root,
                    "public_key": pk,
                    "signature": sig,
                }
            ],
        }
        result = verify_anchor_attestations(anchor)
        self.assertTrue(result["valid"])
        self.assertEqual(result["valid_count"], 1)

    def test_verify_message_roundtrip(self):
        msg = "test-merkle-root"
        sig = sign_message(msg)
        if not sig:
            self.skipTest("POCP_NODE_PRIVATE_KEY not set")
        from services.federation_crypto import get_node_public_key_hex

        pk = get_node_public_key_hex()
        self.assertTrue(verify_message(msg, sig, pk))


if __name__ == "__main__":
    unittest.main()
