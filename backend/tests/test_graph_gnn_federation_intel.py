import unittest

from intelligence.federation_intel import protocol_excerpt_from_bundle, summarize_federation_ingest
from services.graph_gnn_advisory import build_gnn_advisory, pagerank_scores


class GraphGnnAdvisoryTests(unittest.TestCase):
    def test_pagerank_favors_hub(self):
        edges = [
            {"source": "a", "target": "hub", "relation": "x"},
            {"source": "b", "target": "hub", "relation": "x"},
            {"source": "c", "target": "hub", "relation": "x"},
            {"source": "hub", "target": "d", "relation": "y"},
        ]
        scores = pagerank_scores(edges)
        self.assertGreater(scores.get("hub", 0), scores.get("a", 0))

    def test_build_gnn_advisory_contribution_hints(self):
        graph = {
            "nodes": [
                {"id": "e1", "entity_type": "human", "name": "Alice"},
                {"id": "contribution:c1", "entity_type": "contribution", "name": "Doc"},
            ],
            "edges": [
                {"source": "e1", "target": "contribution:c1", "relation": "submits"},
            ],
        }
        result = build_gnn_advisory(graph)
        self.assertTrue(result["advisory_only"])
        self.assertIn("contribution_gnn_hints", result)


class FederationIntelV2Tests(unittest.TestCase):
    def test_summarize_includes_finalization_and_invocation(self):
        packet = {
            "export_type": "pocp_federation_intelligence_v0.2",
            "source_node_id": "node-a",
            "contribution_id": "c1",
            "proof_hash": "abc",
            "finalization": {"mode": "witness_quorum", "finalizer_entity_id": "agent-1"},
            "invocation_trace": {"trace_count": 2},
            "intelligence_packet": {"status": "approved", "participants": [{}, {}]},
        }
        summary = summarize_federation_ingest(packet)
        self.assertEqual(summary["finalization_mode"], "witness_quorum")
        self.assertEqual(summary["invocation_trace_count"], 2)

    def test_protocol_excerpt_from_bundle(self):
        proof = {
            "integrity": {"proof_hash": "xyz"},
            "invocation_trace": {"trace_count": 1},
            "finalization": {"mode": "manual"},
        }
        bundle = {
            "export_type": "pocp_federation_intelligence_v0.2",
            "intelligence_packet": {"verification": {"ai_results": []}},
        }
        excerpt = protocol_excerpt_from_bundle(proof, bundle)
        self.assertEqual(excerpt["proof_hash"], "xyz")
        self.assertEqual(excerpt["intelligence_export_type"], "pocp_federation_intelligence_v0.2")


if __name__ == "__main__":
    unittest.main()
