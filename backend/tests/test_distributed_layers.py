import os
import unittest
from unittest.mock import MagicMock, patch

from services.compute_registry import compute_status_manifest
from services.embedding_match import cosine_similarity, embedding_provider
from services.graph_analytics import _degree_centrality
from services.verifiers.vllm_verifier import VllmVerifier


class DistributedLayerTests(unittest.TestCase):
    def test_cosine_similarity_identical(self):
        v = [1.0, 0.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(v, v), 1.0)

    def test_degree_centrality_normalizes(self):
        edges = [
            {"source": "a", "target": "b", "relation": "x"},
            {"source": "b", "target": "c", "relation": "x"},
        ]
        c = _degree_centrality(edges)
        self.assertEqual(c["b"], 1.0)
        self.assertLess(c["a"], 1.0)

    def test_compute_status_manifest_includes_mock(self):
        manifest = compute_status_manifest()
        self.assertIn("node_id", manifest)
        self.assertIn("active_adapters", manifest)
        self.assertIn("mock", manifest["active_adapters"])

    @patch.dict(os.environ, {"ENABLE_VLLM_VERIFIER": "true"}, clear=False)
    def test_vllm_verifier_available_flag(self):
        v = VllmVerifier()
        self.assertTrue(v.available)

    @patch.dict(os.environ, {"ENABLE_LLAMA_CPP_VERIFIER": "true"}, clear=False)
    def test_llama_cpp_in_compute_manifest_when_enabled(self):
        from services.verifiers.llama_cpp_verifier import LlamaCppVerifier

        self.assertTrue(LlamaCppVerifier().available)
        manifest = compute_status_manifest()
        self.assertIn("llama_cpp", manifest["active_adapters"])

    @patch.dict(os.environ, {"ENABLE_CREWAI_WITNESS": "true"}, clear=False)
    def test_crewai_in_compute_manifest_when_enabled(self):
        from services.crewai_witness import crewai_witness_enabled

        self.assertTrue(crewai_witness_enabled())
        manifest = compute_status_manifest()
        self.assertIn("crewai", manifest["active_adapters"])

    def test_embedding_provider_none_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ENABLE_SENTENCE_TRANSFORMERS", None)
            os.environ.pop("ENABLE_OLLAMA_EMBEDDINGS", None)
            self.assertIsNone(embedding_provider())

    @patch("services.finalization.approve_contribution")
    @patch("services.finalization.is_auto_finalization_enabled", return_value=True)
    def test_graph_analytics_structure(self, *_mocks):
        from services.graph_analytics import build_graph_analytics

        db = MagicMock()
        with patch("services.graph_analytics.build_contribution_graph") as mock_graph:
            mock_graph.return_value = {"nodes": [], "edges": [], "entity_count": 0}
            db.query.return_value.options.return_value.filter.return_value.all.return_value = []
            result = build_graph_analytics(db)
        self.assertTrue(result["advisory_only"])
        self.assertIn("review_queue_hints", result)
        self.assertIn("sourcecred_advisory", result)
        self.assertEqual(result["sourcecred_advisory"]["inspiration"], "github:sourcecred/sourcecred")
        self.assertEqual(result["method"], "pagerank_v0.1")


if __name__ == "__main__":
    unittest.main()
