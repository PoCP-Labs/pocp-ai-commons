"""Tests for optional POCP_PEER_DIALOGUE_HMAC on federation dialogue (CIP-P3.3)."""

import os
import time
import unittest

from services.federation_peers import (
    build_dialogue_hmac_headers,
    clear_dialogue_hmac_cache,
    dialogue_body_digest,
    peer_dialogue_hmac_required,
    verify_incoming_dialogue_hmac,
)


class FederationDialogueHmacTests(unittest.TestCase):
    def setUp(self):
        clear_dialogue_hmac_cache()
        self._secret_prev = os.environ.get("POCP_PEER_DIALOGUE_HMAC")
        self._required_prev = os.environ.get("POCP_PEER_DIALOGUE_HMAC_REQUIRED")
        os.environ["POCP_PEER_DIALOGUE_HMAC"] = "dialogue-test-secret"
        os.environ.pop("POCP_PEER_DIALOGUE_HMAC_REQUIRED", None)
        os.environ.pop("POCP_PEER_DIALOGUE_HMAC_TRUSTED_ONLY", None)

    def tearDown(self):
        clear_dialogue_hmac_cache()
        if self._secret_prev is None:
            os.environ.pop("POCP_PEER_DIALOGUE_HMAC", None)
        else:
            os.environ["POCP_PEER_DIALOGUE_HMAC"] = self._secret_prev
        if self._required_prev is None:
            os.environ.pop("POCP_PEER_DIALOGUE_HMAC_REQUIRED", None)
        else:
            os.environ["POCP_PEER_DIALOGUE_HMAC_REQUIRED"] = self._required_prev

    def test_build_and_verify_round_trip(self):
        body = {"kind": "ping", "from": {"node_id": "node-a"}, "dialogue_id": "d1"}
        headers = build_dialogue_hmac_headers(body, source_node_id="node-a")
        lowered = {k.lower(): v for k, v in headers.items()}
        result = verify_incoming_dialogue_hmac(body, lowered)
        self.assertTrue(result.ok)
        self.assertEqual(result.node_id, "node-a")

    def test_optional_mode_allows_unsigned(self):
        body = {"kind": "ping", "dialogue_id": "d2"}
        result = verify_incoming_dialogue_hmac(body, {})
        self.assertTrue(result.ok)
        self.assertFalse(peer_dialogue_hmac_required())

    def test_required_mode_rejects_unsigned(self):
        os.environ["POCP_PEER_DIALOGUE_HMAC_REQUIRED"] = "true"
        body = {"kind": "ping", "dialogue_id": "d3"}
        result = verify_incoming_dialogue_hmac(body, {})
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "missing_dialogue_hmac_headers")

    def test_rejects_replayed_nonce(self):
        body = {"kind": "ping", "from": {"node_id": "node-a"}, "dialogue_id": "d4"}
        headers = build_dialogue_hmac_headers(body, source_node_id="node-a")
        lowered = {k.lower(): v for k, v in headers.items()}
        self.assertTrue(verify_incoming_dialogue_hmac(body, lowered).ok)
        replay = verify_incoming_dialogue_hmac(body, lowered)
        self.assertFalse(replay.ok)
        self.assertEqual(replay.reason, "nonce_replay")

    def test_rejects_tampered_body(self):
        body = {"kind": "ping", "from": {"node_id": "node-a"}, "dialogue_id": "d5"}
        headers = build_dialogue_hmac_headers(body, source_node_id="node-a")
        tampered = {**body, "kind": "invoke"}
        lowered = {k.lower(): v for k, v in headers.items()}
        result = verify_incoming_dialogue_hmac(tampered, lowered)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "body_digest_mismatch")

    def test_rejects_stale_timestamp(self):
        body = {"kind": "ping", "from": {"node_id": "node-a"}, "dialogue_id": "d6"}
        old_ts = int(time.time()) - 10_000
        digest = dialogue_body_digest(body)
        import hashlib
        import hmac
        from services.federation_peers import dialogue_hmac_message

        message = dialogue_hmac_message(
            node_id="node-a",
            nonce="fixed-nonce",
            timestamp=old_ts,
            body_digest=digest,
        )
        signature = hmac.new(
            b"dialogue-test-secret",
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers = {
            "x-pocp-dialogue-node-id": "node-a",
            "x-pocp-dialogue-nonce": "fixed-nonce",
            "x-pocp-dialogue-timestamp": str(old_ts),
            "x-pocp-dialogue-body-digest": digest,
            "x-pocp-dialogue-signature-alg": "hmac-sha256",
            "x-pocp-dialogue-signature": signature,
        }
        result = verify_incoming_dialogue_hmac(body, headers)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "timestamp_out_of_range")


if __name__ == "__main__":
    unittest.main()
