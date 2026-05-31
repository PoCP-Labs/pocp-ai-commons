import asyncio
import json
import os
import sys
import types
import unittest
from unittest.mock import patch

try:
    import httpx  # noqa: F401
except ModuleNotFoundError:
    sys.modules["httpx"] = types.SimpleNamespace(AsyncClient=None, Client=None)

from services.ollama_client import extract_json_object, ollama_chat_model
from services.embedding_match import blend_keyword_and_embedding, cosine_similarity
from services.verifiers.ollama_verifier import OllamaVerifier


class _FakeChatResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "message": {
                "content": json.dumps(
                    {
                        "task_match": 0.9,
                        "quality": 0.85,
                        "originality": 0.7,
                        "impact": 0.6,
                        "evidence_score": 0.8,
                        "risk_score": 0.1,
                        "suggested_cp": 15,
                        "suggested_credits": 30,
                        "rationale": "Local model agrees with evidence.",
                        "concerns": [],
                    }
                )
            }
        }


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, **kwargs):
        return _FakeChatResponse()


class OllamaVerifierTests(unittest.TestCase):
    def test_extract_json_object_strips_markdown_fence(self):
        raw = '```json\n{"task_match": 0.5}\n```'
        self.assertEqual(extract_json_object(raw)["task_match"], 0.5)

    def test_cosine_similarity_identical_vectors(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)

    def test_blend_without_embeddings_returns_keyword_score(self):
        with patch("services.embedding_match.ollama_embeddings_enabled", return_value=False):
            score = blend_keyword_and_embedding(0.6, "write docs", "documentation agent")
        self.assertEqual(score, 0.6)

    def test_ollama_verify_reports_ollama_provider(self):
        previous = os.environ.get("ENABLE_OLLAMA_VERIFIER")
        os.environ["ENABLE_OLLAMA_VERIFIER"] = "true"
        try:
            with patch("services.ollama_client.httpx.AsyncClient", _FakeAsyncClient):
                result = asyncio.run(
                    OllamaVerifier().verify({"contribution": {"description": "demo"}})
                )
        finally:
            if previous is None:
                os.environ.pop("ENABLE_OLLAMA_VERIFIER", None)
            else:
                os.environ["ENABLE_OLLAMA_VERIFIER"] = previous

        self.assertEqual(result.provider, "ollama")
        self.assertEqual(result.model, ollama_chat_model())
        self.assertEqual(result.task_match, 0.9)
        self.assertEqual(result.risk_score, 0.1)


if __name__ == "__main__":
    unittest.main()
