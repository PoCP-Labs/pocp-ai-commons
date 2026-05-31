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
    sys.modules["httpx"] = types.SimpleNamespace(AsyncClient=None)

from services.verifiers.deepseek_verifier import DeepSeekVerifier
from services.verifiers.openai_verifier import build_verifier_prompt, normalize_result


class _FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "task_match": 1.2,
                                "quality": 0.8,
                                "originality": 0.7,
                                "impact": 0.6,
                                "evidence_score": 0.5,
                                "risk_score": -1,
                                "suggested_cp": 12,
                                "suggested_credits": 48,
                                "rationale": "Evidence supports the contribution.",
                                "concerns": ["Needs human review."],
                            }
                        )
                    }
                }
            ]
        }


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, **kwargs):
        self.requests.append((url, kwargs))
        return _FakeResponse()


class VerifierTests(unittest.TestCase):
    def test_prompt_requires_human_review_and_embeds_context(self):
        context = {
            "task": {"title": "Write docs"},
            "contribution": {"description": "Added setup guide"},
        }

        prompt = build_verifier_prompt(context)

        self.assertIn("You do not approve or reject contributions", prompt)
        self.assertIn("ready_for_policy_finalize", prompt)
        self.assertIn('"title": "Write docs"', prompt)
        self.assertIn('"description": "Added setup guide"', prompt)

    def test_normalize_result_clamps_scores_and_keeps_concerns(self):
        result = normalize_result(
            "openai",
            "test-model",
            {
                "task_match": 2,
                "quality": "bad",
                "originality": 0.25,
                "impact": None,
                "evidence_score": 0.9,
                "risk_score": -3,
                "suggested_cp": 10,
                "suggested_credits": 20,
                "rationale": "Looks useful.",
                "concerns": ["Verify license."],
            },
        )

        self.assertEqual(result.task_match, 1.0)
        self.assertEqual(result.quality, 0.5)
        self.assertEqual(result.impact, 0.5)
        self.assertEqual(result.risk_score, 0.0)
        self.assertEqual(result.concerns, ["Verify license."])

    def test_normalize_result_handles_invalid_reward_values(self):
        result = normalize_result(
            "openai",
            "test-model",
            {
                "suggested_cp": "many",
                "suggested_credits": -50,
                "rationale": "",
                "concerns": None,
            },
        )

        self.assertEqual(result.suggested_cp, 0.0)
        self.assertEqual(result.suggested_credits, 0.0)
        self.assertEqual(result.rationale, "No rationale provided.")
        self.assertEqual(result.concerns, [])

    def test_deepseek_verify_reports_deepseek_provider(self):
        previous_key = os.environ.get("DEEPSEEK_API_KEY")
        os.environ["DEEPSEEK_API_KEY"] = "test-key"
        try:
            with patch("services.verifiers.openai_verifier.httpx.AsyncClient", _FakeAsyncClient):
                result = asyncio.run(DeepSeekVerifier().verify({"contribution": {"description": "demo"}}))
        finally:
            if previous_key is None:
                os.environ.pop("DEEPSEEK_API_KEY", None)
            else:
                os.environ["DEEPSEEK_API_KEY"] = previous_key

        self.assertEqual(result.provider, "deepseek")
        self.assertEqual(result.model, "deepseek-chat")
        self.assertEqual(result.task_match, 1.0)
        self.assertEqual(result.risk_score, 0.0)


if __name__ == "__main__":
    unittest.main()
