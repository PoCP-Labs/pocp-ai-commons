import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from services.peer_compute import (
    PeerComputeNode,
    clear_peer_compute_cache,
    load_peer_compute_nodes,
    peer_compute_enabled,
    select_peer_compute_node,
    validate_peer_witness_request,
)
from services.verifiers.peer_witness_verifier import PeerWitnessVerifier


class PeerComputeTests(unittest.TestCase):
    def tearDown(self):
        clear_peer_compute_cache()
        os.environ.pop("ENABLE_PEER_COMPUTE", None)
        os.environ.pop("POCP_ALLOW_PEER_WITNESS", None)
        os.environ.pop("POCP_PEER_COMPUTE_SECRET", None)

    def test_peer_compute_enabled_via_env(self):
        os.environ["ENABLE_PEER_COMPUTE"] = "true"
        self.assertTrue(peer_compute_enabled())

    @patch("services.peer_compute.load_trusted_nodes")
    @patch("services.peer_compute.load_compute_registry")
    def test_inherit_trusted_nodes(self, mock_registry, mock_trusted):
        mock_registry.return_value = {
            "peer_compute": {"enabled": True, "inherit_trusted_nodes": True, "nodes": []},
        }
        mock_trusted.return_value = [
            MagicMock(node_id="node-b", base_url="http://127.0.0.1:8101", trust_weight=0.8),
        ]
        clear_peer_compute_cache()
        nodes = load_peer_compute_nodes()
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].node_id, "node-b")

    def test_round_robin_selection(self):
        nodes = (
            PeerComputeNode("a", "http://a"),
            PeerComputeNode("b", "http://b"),
        )
        with patch("services.peer_compute.load_peer_compute_nodes", return_value=nodes):
            first = select_peer_compute_node("round_robin")
            second = select_peer_compute_node("round_robin")
        self.assertNotEqual(first.node_id, second.node_id)

    def test_peer_witness_auth_secret(self):
        os.environ["POCP_PEER_COMPUTE_SECRET"] = "sekrit"
        self.assertTrue(validate_peer_witness_request({"x-pocp-peer-secret": "sekrit"}))
        self.assertFalse(validate_peer_witness_request({"x-pocp-peer-secret": "wrong"}))

    def test_peer_witness_auth_allow_flag(self):
        os.environ["POCP_ALLOW_PEER_WITNESS"] = "true"
        self.assertTrue(validate_peer_witness_request({}))

    def test_peer_witness_verifier_parses_response(self):
        peer = PeerComputeNode("node-b", "http://127.0.0.1:8101")
        verifier = PeerWitnessVerifier(peer)

        async def _run():
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "result": {
                    "provider": "mock",
                    "model": "mock-v1",
                    "task_match": 0.8,
                    "quality": 0.8,
                    "originality": 0.7,
                    "impact": 0.7,
                    "evidence_score": 0.8,
                    "risk_score": 0.2,
                    "suggested_cp": 20,
                    "suggested_credits": 50,
                    "rationale": "ok",
                    "concerns": [],
                }
            }
            mock_resp.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            with patch("services.verifiers.peer_witness_verifier.httpx.AsyncClient", return_value=mock_client):
                return await verifier.verify({"task": {}, "contribution": {}})

        import asyncio

        result = asyncio.run(_run())
        self.assertTrue(result.provider.startswith("peer:node-b"))
        self.assertGreaterEqual(result.quality, 0.8)


if __name__ == "__main__":
    unittest.main()
