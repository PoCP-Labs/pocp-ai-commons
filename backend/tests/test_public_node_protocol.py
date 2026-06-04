"""Public node protocol — /pocp/* alias routes (Phase A shim)."""

import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from services.entity_dialogue import ENTITY_DIALOGUE_SCHEMA
from services.federation_discovery import FEDERATION_PEER_MANIFEST_SCHEMA


class PublicNodeProtocolTests(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
        os.environ["POCP_DIALOGUE_PEER_ROUTE"] = "false"
        from database import Base as DbBase, engine

        DbBase.metadata.create_all(bind=engine)
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add(
            Entity(
                entity_type=EntityType.human,
                name="Probe Human",
                status=EntityStatus.active,
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _client(self):
        from fastapi.testclient import TestClient
        from main import app

        return TestClient(app)

    def test_pocp_health(self):
        client = self._client()
        resp = client.get("/pocp/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("surface"), "pocp-public-node")
        self.assertIn(data.get("status"), ("ok", "degraded"))

    def test_pocp_node_manifest(self):
        client = self._client()
        resp = client.get("/pocp/node")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("endpoints", data)
        endpoints = data["endpoints"]
        self.assertIn("pocp_invoke", endpoints)
        self.assertIn("pocp_capabilities", endpoints)

    def test_pocp_capabilities_directory(self):
        client = self._client()
        resp = client.get("/pocp/capabilities")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("items", data)

    def test_pocp_protocol_surface(self):
        client = self._client()
        resp = client.get("/pocp/protocol")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["schema"], "pocp.public_node_protocol.v0.1")

    def test_pocp_sync_manifest(self):
        client = self._client()
        resp = client.get("/pocp/sync")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["schema"], "pocp.public_node_sync.v0.1")
        self.assertEqual(data["manifest"]["schema"], FEDERATION_PEER_MANIFEST_SCHEMA)

    def test_pocp_invoke_ping(self):
        from services.network.dialogue_route import local_node_id

        client = self._client()
        human = self.db.query(Entity).first()
        node = local_node_id()
        ref = {"entity_id": human.id, "node_id": node}
        envelope = {
            "schema": ENTITY_DIALOGUE_SCHEMA,
            "dialogue_id": "dlg_pocp_public_1",
            "kind": "ping",
            "from": ref,
            "to": ref,
            "payload": {},
        }
        resp = client.post("/pocp/invoke", json=envelope)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("status"), "accepted")

    def test_well_known_includes_pocp_endpoints(self):
        from services.node.schemas import build_instance_endpoints

        endpoints = build_instance_endpoints(backend_url="http://127.0.0.1:8000")
        self.assertIn("pocp_invoke", endpoints)
        self.assertIn("pocp_health", endpoints)


if __name__ == "__main__":
    unittest.main()
