"""Tests for llama.cpp OpenAI-compatible witness adapter."""

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

from services.verifiers.llama_cpp_verifier import LlamaCppVerifier


class _FakeChatResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "model": "llama",
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "task_match": 0.88,
                                "quality": 0.82,
                                "originality": 0.65,
                                "impact": 0.55,
                                "evidence_score": 0.75,
                                "risk_score": 0.12,
                                "suggested_cp": 12,
                                "suggested_credits": 24,
                                "rationale": "llama.cpp local witness.",
                                "concerns": [],
                            }
                        )
                    }
                }
            ],
        }


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self.last_url = None
        self.last_payload = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, **kwargs):
        self.last_url = url
        self.last_payload = kwargs.get("json")
        return _FakeChatResponse()


class LlamaCppVerifierTests(unittest.TestCase):
    @patch.dict(os.environ, {"ENABLE_LLAMA_CPP_VERIFIER": "true"}, clear=False)
    def test_available_flag(self):
        self.assertTrue(LlamaCppVerifier().available)

    def test_verify_reports_llama_cpp_provider(self):
        previous = os.environ.get("ENABLE_LLAMA_CPP_VERIFIER")
        os.environ["ENABLE_LLAMA_CPP_VERIFIER"] = "true"
        try:
            fake = _FakeAsyncClient()
            with patch("services.verifiers.llama_cpp_verifier.httpx.AsyncClient", lambda *a, **k: fake):
                result = asyncio.run(
                    LlamaCppVerifier().verify({"contribution": {"description": "edge witness demo"}})
                )
        finally:
            if previous is None:
                os.environ.pop("ENABLE_LLAMA_CPP_VERIFIER", None)
            else:
                os.environ["ENABLE_LLAMA_CPP_VERIFIER"] = previous

        self.assertEqual(result.provider, "llama_cpp")
        self.assertEqual(result.task_match, 0.88)
        self.assertIn("/v1/chat/completions", fake.last_url)
        self.assertEqual(fake.last_payload["model"], "llama")


if __name__ == "__main__":
    unittest.main()
