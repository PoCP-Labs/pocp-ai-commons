"""CI-5 — federation peer manifests, discovery, and handshake."""

import os
import unittest
from unittest.mock import patch

from services.federation_discovery import (
    FEDERATION_PEER_MANIFEST_SCHEMA,
    build_local_peer_manifest,
    discover_peer_capabilities,
    federation_handshake_with_peer,
    public_skill_node_template,
)


class FederationDiscoveryTests(unittest.TestCase):
    def test_public_skill_node_template_schema(self):
        tpl = public_skill_node_template()
        self.assertEqual(tpl["schema"], "pocp-skill-node-template.v0.1")
        self.assertEqual(tpl["default_capability"]["capability_type"], "code_review")
        self.assertIn("handshake", tpl["endpoints"])

    def test_build_local_peer_manifest(self):
        manifest = build_local_peer_manifest(base_url="http://node-a:8100")
        self.assertEqual(manifest["schema"], FEDERATION_PEER_MANIFEST_SCHEMA)
        self.assertEqual(manifest["base_url"], "http://node-a:8100")
        self.assertTrue(manifest["handshake"].get("handshake_version"))
        self.assertIn("skill_node_template", manifest)

    @patch("services.federation_discovery._get_json")
    def test_discover_peer_capabilities(self, mock_get):
        mock_get.return_value = {
            "capabilities": [
                {"capability_id": "cap_1", "capability_type": "code_review", "name": "Review"},
            ]
        }
        result = discover_peer_capabilities("http://peer-b:8101", capability_type="code_review")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["capabilities"][0]["capability_type"], "code_review")
        mock_get.assert_called_once()
        self.assertIn("code_review", mock_get.call_args[0][0])

    @patch("services.federation_discovery.bundle_fingerprint", return_value="fp_local")
    @patch("services.federation_discovery.fetch_remote_peer_manifest")
    def test_federation_handshake_ok(self, mock_fetch, _mock_fp):
        mock_fetch.return_value = {
            "node_id": "node-b",
            "trust_policy_bundle_fingerprint": "fp_local",
            "handshake": {
                "handshake_version": "pocp-peer-v1",
                "algorithms": ["hmac-sha256"],
            },
        }
        result = federation_handshake_with_peer("http://peer-b:8101")
        self.assertTrue(result["ok"])
        self.assertTrue(result["trust_bundle_aligned"])
        self.assertEqual(result["remote_node_id"], "node-b")

    @patch("services.federation_discovery.fetch_remote_peer_manifest")
    def test_federation_handshake_rejects_missing_algorithms(self, mock_fetch):
        mock_fetch.return_value = {
            "node_id": "node-b",
            "trust_policy_bundle_fingerprint": "fp",
            "handshake": {"handshake_version": "pocp-peer-v1", "algorithms": []},
        }
        with self.assertRaises(ValueError) as ctx:
            federation_handshake_with_peer("http://peer-b:8101")
        self.assertIn("handshake", str(ctx.exception).lower())


class FederationDiscoveryRouterTests(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
        from database import Base, engine

        Base.metadata.create_all(bind=engine)

    def test_local_manifest_route(self):
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        resp = client.get("/api/v1/federation/peers/manifest")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["schema"], FEDERATION_PEER_MANIFEST_SCHEMA)
        self.assertTrue(data.get("handshake"))

    def test_skill_node_template_route(self):
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        resp = client.get("/api/v1/federation/skill-node-template")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["schema"], "pocp-skill-node-template.v0.1")


if __name__ == "__main__":
    unittest.main()
