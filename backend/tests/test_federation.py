import json
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

try:
    import httpx  # noqa: F401
except ModuleNotFoundError:
    sys.modules["httpx"] = types.SimpleNamespace(AsyncClient=None, Client=None)

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from services.federation_crypto import (
    import_payload_message,
    sign_message,
    verify_message,
)
from services.federation_sync import sync_peers_http


class FederationCryptoTests(unittest.TestCase):
    def setUp(self):
        self._prev_priv = os.environ.get("POCP_NODE_PRIVATE_KEY")
        self._prev_pub = os.environ.get("POCP_NODE_PUBLIC_KEY")
        private = Ed25519PrivateKey.generate()
        self.private_hex = private.private_bytes_raw().hex()
        self.public_hex = private.public_key().public_bytes_raw().hex()
        os.environ["POCP_NODE_PRIVATE_KEY"] = self.private_hex
        os.environ["POCP_NODE_PUBLIC_KEY"] = self.public_hex

    def tearDown(self):
        if self._prev_priv is None:
            os.environ.pop("POCP_NODE_PRIVATE_KEY", None)
        else:
            os.environ["POCP_NODE_PRIVATE_KEY"] = self._prev_priv
        if self._prev_pub is None:
            os.environ.pop("POCP_NODE_PUBLIC_KEY", None)
        else:
            os.environ["POCP_NODE_PUBLIC_KEY"] = self._prev_pub

    def test_sign_and_verify_import_payload_message(self):
        message = import_payload_message(
            source_node_id="node-a",
            contribution_id="contrib-1",
            primary_entity_portable_id="dev:rain@example.com",
            evidence_hash="abc123",
            ledger_record_hash="ledger-tip",
        )
        signature = sign_message(message)
        self.assertTrue(signature)
        self.assertTrue(verify_message(message, signature, self.public_hex))
        self.assertFalse(verify_message(message + "tampered", signature, self.public_hex))


class FederationSyncHttpTests(unittest.TestCase):
    @patch("services.federation_peers.post_import_proof")
    @patch("services.federation_sync.fetch_proof")
    @patch("services.federation_sync._export_approved_contribution_ids")
    def test_sync_peers_http_imports_proofs(self, mock_export, mock_fetch, mock_post):
        mock_export.return_value = ["c1"]
        mock_fetch.return_value = {"proof_type": "pocp_contribution_proof", "integrity": {}}
        mock_post.return_value = {"id": "import-1", "reputation_applied": 4.0}

        os.environ["POCP_MIRROR_SOURCES"] = json.dumps(
            [{"node_id": "node-a", "base_url": "http://peer-a:8000", "public_key": "aa" * 32}]
        )
        summary = sync_peers_http("http://mirror:8000")

        self.assertEqual(summary["target"], "http://mirror:8000")
        self.assertEqual(len(summary["results"]), 1)
        self.assertEqual(summary["results"][0]["status"], "imported")
        mock_post.assert_called_once()


class FederationImportSignatureTests(unittest.TestCase):
    def test_rejects_invalid_proof_hash(self):
        from fastapi import HTTPException
        from services.federation_import import _verify_proof_signature
        from schemas.federation import TrustedNode

        trusted = {
            "node-a": TrustedNode(
                node_id="node-a",
                base_url="http://a",
                public_key="10" * 32,
                trust_weight=0.8,
            )
        }
        proof = {
            "integrity": {"proof_hash": "deadbeef"},
            "federation": {"signature": "00" * 64, "node_id": "node-a"},
        }
        with patch("services.federation_import.compute_contribution_proof_hash", return_value="other"):
            with self.assertRaises(HTTPException) as ctx:
                _verify_proof_signature("node-a", proof, trusted)
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("hash mismatch", ctx.exception.detail)


class ProofHashTests(unittest.TestCase):
    def test_compute_hash_stable_after_json_roundtrip(self):
        import json

        from services.proof import compute_contribution_proof_hash

        proof = {
            "spec_version": "0.1",
            "proof_type": "pocp_contribution_proof",
            "contribution_event": {"id": "c1", "status": "approved"},
            "expert_cards": [{"title": "demo"}],
            "code_attribution_context": {"paths": []},
            "integrity": {
                "evidence_hash": "abc",
                "hash_algorithm": "sha256",
            },
        }
        proof["integrity"]["proof_hash"] = compute_contribution_proof_hash(proof)
        roundtrip = json.loads(json.dumps(proof))
        self.assertEqual(
            proof["integrity"]["proof_hash"],
            compute_contribution_proof_hash(roundtrip),
        )


if __name__ == "__main__":
    unittest.main()
