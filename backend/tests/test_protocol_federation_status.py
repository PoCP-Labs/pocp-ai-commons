"""CIP-P0.2 — federation protocol operator manifest."""

import os
import unittest

from services.node.schemas import FEDERATION_PROTOCOL_MANIFEST_SCHEMA, build_operator_protocol_endpoints
from services.protocol_federation_status.schemas import (
    federation_protocol_manifest,
    validate_federation_protocol_manifest,
)


class ProtocolFederationStatusTests(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
        from database import Base, engine
        from sqlalchemy.orm import sessionmaker

        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()

    def test_operator_endpoints_include_pocp_and_exchange_import(self):
        endpoints = build_operator_protocol_endpoints(backend_url="http://127.0.0.1:8000")
        self.assertIn("pocp_invoke", endpoints)
        self.assertIn("federation_exchange_import", endpoints)
        self.assertIn("ai_chat", endpoints)
        self.assertIn("mcp_invoke", endpoints)

    def test_federation_protocol_manifest_shape(self):
        manifest = federation_protocol_manifest(self.db)
        self.assertEqual(manifest["schema"], FEDERATION_PROTOCOL_MANIFEST_SCHEMA)
        self.assertTrue(manifest.get("operator_surface"))
        self.assertIn("addrbook", manifest)
        self.assertIn("feature_flags", manifest)
        self.assertIn("promotion_policy", manifest)
        validate_federation_protocol_manifest(manifest)

    def test_federation_protocol_route(self):
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        resp = client.get("/api/v1/intelligence/protocol/federation")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["schema"], FEDERATION_PROTOCOL_MANIFEST_SCHEMA)
        self.assertIn("pocp_invoke", data["endpoints"])
        self.assertIn("federation_exchange_import", data["endpoints"])


if __name__ == "__main__":
    unittest.main()
