"""CIP-P4.1 — PoCP Node Python SDK against in-process /pocp/* routes."""

import os
import unittest
import urllib.error

from sqlalchemy.orm import sessionmaker

from models.entity import Entity, EntityStatus, EntityType
from services.entity_dialogue import ENTITY_DIALOGUE_SCHEMA
from services.proof import compute_contribution_proof_hash
from services.verify_standalone import verify_proof_integrity
from sdk.pocp_node_client import PocpNodeClient


class PocpNodeSdkTests(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
        os.environ["POCP_DIALOGUE_PEER_ROUTE"] = "false"
        from database import Base as DbBase, engine

        DbBase.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()
        self.db.add(
            Entity(
                entity_type=EntityType.human,
                name="SDK Human",
                status=EntityStatus.active,
            )
        )
        self.db.commit()
        self.human_id = self.db.query(Entity).filter(Entity.name == "SDK Human").first().id

    def tearDown(self):
        self.db.close()

    def _client(self):
        from fastapi.testclient import TestClient
        from main import app

        return TestClient(app)

    def _sdk(self) -> PocpNodeClient:
        http = self._client()
        return PocpNodeClient("http://testserver", transport=_TestClientTransport(http))

    def test_health_and_manifest(self):
        sdk = self._sdk()
        health = sdk.health()
        self.assertEqual(health.get("surface"), "pocp-public-node")
        manifest = sdk.refresh_manifest()
        self.assertIn("endpoints", manifest)
        self.assertIn("pocp_invoke", sdk._endpoints)

    def test_capabilities_directory(self):
        sdk = self._sdk()
        data = sdk.capabilities(limit=10)
        self.assertIn("items", data)

    def test_ping_invoke(self):
        from services.network.dialogue_route import local_node_id

        sdk = self._sdk()
        node = local_node_id()
        response = sdk.ping(entity_id=self.human_id, node_id=node)
        self.assertEqual(response.get("status"), "accepted")

    def test_quote_invoke_envelope(self):
        from services.entity_register import register_entity

        skill = register_entity(
            self.db,
            entity_type="skill",
            name="SDK Skill",
            description="Skill",
            owner_id=self.human_id,
            creator_id=self.human_id,
        )
        from models.wallet import Wallet

        self.db.add(Wallet(entity_id=self.human_id, ai_credits=50, cp_balance=0))
        self.db.commit()

        from services.network.dialogue_route import local_node_id

        node = local_node_id()
        sdk = self._sdk()
        response = sdk.quote(
            from_ref={"entity_id": self.human_id, "node_id": node},
            to_ref={"entity_id": skill.id, "node_id": node},
            payload={"quote_action": "capability_invoke"},
        )
        self.assertEqual(response.get("status"), "accepted")
        self.assertTrue(response.get("result", {}).get("quote", {}).get("allowed"))

    def test_verify_proof_via_pocp_proofs(self):
        proof = self._minimal_proof()
        local = verify_proof_integrity(proof)
        self.assertTrue(local["valid"])

        sdk = self._sdk()
        routed = sdk.verify_proof(proof)
        self.assertTrue(routed.get("valid"), routed)

    def test_connect_self_probe(self):
        sdk = self._sdk()
        result = sdk.connect("http://testserver")
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("schema"), "pocp.sdk_peer_connect.v0.1")

    def test_dialogue_envelope_schema(self):
        env = PocpNodeClient.dialogue_envelope(
            kind="ping",
            from_ref={"entity_id": "a", "node_id": "n"},
            to_ref={"entity_id": "b", "node_id": "n"},
        )
        self.assertEqual(env["schema"], ENTITY_DIALOGUE_SCHEMA)
        self.assertEqual(env["kind"], "ping")

    def _minimal_proof(self) -> dict:
        from datetime import datetime

        from services.ledger_chain import compute_record_hash

        t0 = datetime(2026, 1, 1, 12, 0, 0)
        h0 = compute_record_hash(None, "contribution_approved", {"cp": 10}, t0)
        proof = {
            "spec_version": "0.1",
            "proof_type": "pocp_contribution_proof",
            "proof_id": "proof-sdk-test",
            "contribution_event": {"id": "contrib-sdk", "status": "approved"},
            "finalization": {
                "finalizer_entity_id": "pocp-entity-clarion-0",
                "mode": "witness_quorum",
                "policy_id": "entity_equal_auto_v1",
            },
            "verification": {
                "entity_finalizations": [
                    {"approved": True, "finalizer_entity_id": "pocp-entity-clarion-0"}
                ],
            },
            "ledger_audit": {
                "records": [
                    {
                        "id": "r0",
                        "event_type": "contribution_approved",
                        "payload": {"cp": 10},
                        "prev_hash": None,
                        "record_hash": h0,
                        "created_at": t0.isoformat(),
                    }
                ],
                "record_hashes": [h0],
            },
        }
        proof["integrity"] = {
            "ledger_tip_hash": h0,
            "hash_algorithm": "sha256",
        }
        proof["integrity"]["proof_hash"] = compute_contribution_proof_hash(proof)
        return proof


class _TestClientTransport:
    """Route SDK HTTP calls through FastAPI TestClient (in-process, no socket)."""

    def __init__(self, client):
        self._client = client

    def open(self, request):  # noqa: ANN001 — urllib handler protocol
        import io
        import json as _json
        from urllib.parse import parse_qs, urlparse
        from urllib.response import addinfourl

        url = request.full_url
        parsed = urlparse(url)
        path = parsed.path
        method = request.get_method()
        body = None
        if request.data:
            body = _json.loads(request.data.decode("utf-8"))
        if method == "GET":
            params = {k: v[0] for k, v in parse_qs(parsed.query).items()} or None
            resp = self._client.get(path, params=params)
        else:
            resp = self._client.request(method, path, json=body)
        payload = resp.content
        if resp.status_code >= 400:
            raise urllib.error.HTTPError(
                url,
                resp.status_code,
                resp.reason_phrase,
                resp.headers,
                io.BytesIO(payload),
            )
        return addinfourl(io.BytesIO(payload), resp.headers, url)


if __name__ == "__main__":
    unittest.main()
