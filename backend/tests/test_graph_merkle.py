"""Tests for Contribution Graph Merkle commitment and SPV inclusion."""

import unittest

from services.graph_merkle import (
    build_contribution_graph_inclusion,
    build_graph_merkle_root,
    canonical_edge_key,
    edge_leaf_hash,
    verify_graph_merkle_inclusion,
)


class GraphMerkleTests(unittest.TestCase):
    def test_canonical_edge_stable(self):
        edge = {
            "source": "e1",
            "target": "contribution:c1",
            "relation": "submits",
            "contribution_id": "c1",
            "weight": 0.4,
        }
        self.assertEqual(canonical_edge_key(edge), canonical_edge_key(edge))
        self.assertEqual(len(edge_leaf_hash(edge)), 64)

    def test_graph_merkle_root_order_independent(self):
        e1 = {
            "source": "a",
            "target": "b",
            "relation": "uses",
            "contribution_id": "c1",
            "weight": 1.0,
        }
        e2 = {
            "source": "b",
            "target": "c",
            "relation": "calls",
            "contribution_id": "c1",
            "weight": 1.0,
        }
        root_a = build_graph_merkle_root([e1, e2])
        root_b = build_graph_merkle_root([e2, e1])
        self.assertEqual(root_a, root_b)

    def test_contribution_inclusion_roundtrip(self):
        edges = [
            {
                "source": "human-1",
                "target": "contribution:contrib-1",
                "relation": "submits",
                "contribution_id": "contrib-1",
                "weight": 0.4,
            },
            {
                "source": "agent-1",
                "target": "contribution:contrib-1",
                "relation": "witnesses",
                "contribution_id": "contrib-1",
                "weight": 0.2,
            },
            {
                "source": "rain",
                "target": "agent-1",
                "relation": "owns",
                "contribution_id": None,
                "weight": 1.0,
            },
        ]
        inclusion = build_contribution_graph_inclusion(edges, "contrib-1")
        assert inclusion is not None
        self.assertEqual(inclusion["edge_count"], 2)
        self.assertTrue(verify_graph_merkle_inclusion(inclusion))

    def test_verify_rejects_tampered_proof(self):
        edges = [
            {
                "source": "a",
                "target": "contribution:x",
                "relation": "submits",
                "contribution_id": "x",
                "weight": 1.0,
            },
        ]
        inclusion = build_contribution_graph_inclusion(edges, "x")
        assert inclusion is not None
        inclusion["proofs"][0]["leaf_hash"] = "0" * 64
        self.assertFalse(verify_graph_merkle_inclusion(inclusion))


if __name__ == "__main__":
    unittest.main()
