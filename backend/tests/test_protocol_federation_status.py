"""Tests for federation protocol manifest (L1 HTTPS binding)."""

import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from services.protocol_federation_status import federation_protocol_manifest


class FederationProtocolManifestTests(unittest.TestCase):
    def test_manifest_schema_and_features(self):
        manifest = federation_protocol_manifest()
        self.assertEqual(manifest["schema"], "pocp.federation_protocol_manifest.v0.1")
        self.assertEqual(manifest["stack_layer"], "L1_federation_binding")
        self.assertIn("dialogue_peer_route", manifest["features"])
        self.assertIn("connect", manifest["endpoints"])
        self.assertIn("cross_node_dialogue", manifest["endpoints"])
        self.assertIn("import_exchange_proof", manifest["endpoints"])
        self.assertIn("operator_manifest", manifest)
        self.assertIn("public_node", manifest)
        self.assertIn("exchange_import", manifest)
        self.assertIn("pocp_invoke", manifest["public_node"]["endpoints"])
        op = manifest["operator_manifest"]
        self.assertIn("well_known", op)
        self.assertIn("exchange_proof_import", op)

    def test_manifest_with_db_peer_counts(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            manifest = federation_protocol_manifest(db)
            self.assertIn("discovered_count", manifest["peers"])
            self.assertEqual(manifest["peers"]["discovered_count"], 0)
        finally:
            db.close()


class FederationProtocolRouterTests(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
        from database import Base, engine

        Base.metadata.create_all(bind=engine)

    def test_protocol_federation_route(self):
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        resp = client.get("/api/v1/intelligence/protocol/federation")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["schema"], "pocp.federation_protocol_manifest.v0.1")
        self.assertIn("endpoints", data)
        self.assertIn("promotion_policy", data)
        self.assertIn("public_node", data)
        self.assertIn("exchange_import", data)
        self.assertEqual(
            data["exchange_import"]["endpoints"]["import_exchange_proof"],
            "POST /api/v1/federation/import-exchange-proof",
        )


if __name__ == "__main__":
    unittest.main()
