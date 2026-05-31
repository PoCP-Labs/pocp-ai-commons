"""Tests for AGT-inspired peer trust handshake (BI-2)."""

import os
import time
import unittest
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from services.federation_crypto import sign_message, verify_message
from services.peer_compute import validate_peer_witness_request
from services.peer_trust import (
    build_peer_auth_headers,
    clear_peer_trust_cache,
    handshake_message,
    issue_peer_challenge,
    verify_peer_handshake,
)


class PeerTrustTests(unittest.TestCase):
    def setUp(self):
        clear_peer_trust_cache()
        os.environ["POCP_PEER_COMPUTE_SECRET"] = "test-shared-secret"
        os.environ.pop("POCP_ALLOW_PEER_WITNESS", None)

    def tearDown(self):
        clear_peer_trust_cache()
        os.environ.pop("POCP_PEER_COMPUTE_SECRET", None)
        os.environ.pop("POCP_PEER_HANDSHAKE_MODE", None)
        os.environ.pop("POCP_NODE_PRIVATE_KEY", None)
        os.environ.pop("POCP_NODE_PUBLIC_KEY", None)

    def test_build_and_verify_hmac_handshake(self):
        headers = build_peer_auth_headers(source_node_id="node-a")
        result = verify_peer_handshake({k.lower(): v for k, v in headers.items()})
        self.assertTrue(result.ok)
        self.assertEqual(result.algorithm, "hmac-sha256")
        self.assertTrue(validate_peer_witness_request({k.lower(): v for k, v in headers.items()}))

    def test_rejects_replayed_nonce(self):
        headers = build_peer_auth_headers(source_node_id="node-a", nonce="fixed-nonce")
        lowered = {k.lower(): v for k, v in headers.items()}
        self.assertTrue(verify_peer_handshake(lowered).ok)
        replay = verify_peer_handshake(lowered)
        self.assertFalse(replay.ok)
        self.assertEqual(replay.reason, "nonce_replay")

    def test_rejects_stale_timestamp(self):
        old_ts = int(time.time()) - 10_000
        message = handshake_message(node_id="node-a", nonce="n1", timestamp=old_ts)
        import hashlib
        import hmac

        digest = hmac.new(
            b"test-shared-secret",
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers = {
            "x-pocp-peer-node-id": "node-a",
            "x-pocp-peer-nonce": "n1",
            "x-pocp-peer-timestamp": str(old_ts),
            "x-pocp-peer-signature": digest,
            "x-pocp-peer-signature-alg": "hmac-sha256",
        }
        result = verify_peer_handshake(headers)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "timestamp_out_of_range")

    def test_challenge_mode_requires_issued_nonce(self):
        os.environ["POCP_PEER_HANDSHAKE_MODE"] = "challenge"
        challenge = issue_peer_challenge(node_id="node-b")
        headers = build_peer_auth_headers(
            source_node_id="node-b",
            nonce=challenge["nonce"],
        )
        lowered = {k.lower(): v for k, v in headers.items()}
        self.assertTrue(verify_peer_handshake(lowered).ok)

        bad = build_peer_auth_headers(source_node_id="node-b", nonce="not-issued")
        self.assertFalse(verify_peer_handshake({k.lower(): v for k, v in bad.items()}).ok)

    def test_ed25519_handshake_with_trusted_key(self):
        private = Ed25519PrivateKey.generate()
        public_hex = private.public_key().public_bytes_raw().hex()
        os.environ["POCP_NODE_PRIVATE_KEY"] = private.private_bytes_raw().hex()
        os.environ["POCP_NODE_PUBLIC_KEY"] = public_hex

        with mock.patch("services.peer_trust.trusted_nodes_map") as mock_map:
            mock_map.return_value = {
                "node-ed": mock.Mock(public_key=public_hex, node_id="node-ed"),
            }
            ts = int(time.time())
            nonce = "ed-nonce"
            message = handshake_message(node_id="node-ed", nonce=nonce, timestamp=ts)
            signature = sign_message(message)
            headers = {
                "x-pocp-peer-node-id": "node-ed",
                "x-pocp-peer-nonce": nonce,
                "x-pocp-peer-timestamp": str(ts),
                "x-pocp-peer-signature": signature,
                "x-pocp-peer-signature-alg": "ed25519",
            }
            result = verify_peer_handshake(headers)
            self.assertTrue(result.ok)
            self.assertEqual(result.algorithm, "ed25519")
            self.assertTrue(verify_message(message, signature, public_hex))


if __name__ == "__main__":
    unittest.main()
