import asyncio
import unittest

from services.ai_verify_service import AiVerifyRubric, ai_verify_service


class AiVerifyServiceTests(unittest.TestCase):
    def test_simulated_provider_returns_rubric(self):
        rubric = asyncio.run(
            ai_verify_service(
                task_title="Write docs",
                contribution_description="Added a setup guide with examples.",
                evidence={"url": "https://example.com/guide"},
                participants=[{"entity_id": "e1", "role": "creator", "weight": 1.0}],
                provider="simulated",
            )
        )

        self.assertIsInstance(rubric, AiVerifyRubric)
        self.assertEqual(rubric.provider, "mock")
        self.assertGreater(rubric.score, 0.0)
        self.assertTrue(rubric.feedback)

    def test_score_zero_uses_ai_path_contract(self):
        rubric = asyncio.run(
            ai_verify_service(
                contribution_description="",
                evidence={},
                provider="simulated",
            )
        )

        self.assertLess(rubric.evidence_score, 0.5)
        self.assertIn("Evidence", " ".join(rubric.concerns))


if __name__ == "__main__":
    unittest.main()
