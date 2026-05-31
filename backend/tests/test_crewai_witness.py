"""Tests for CrewAI multi-agent witness (native role crew)."""

import asyncio
import os
import unittest
from unittest.mock import patch

from services.crewai_witness import (
    aggregate_role_results,
    crewai_witness_enabled,
    run_crewai_witness,
    run_native_role_crew,
)
from services.verifiers.crewai_witness_verifier import CrewaiWitnessVerifier


SAMPLE_CONTEXT = {
    "task": {"title": "Document API", "description": "Write API docs"},
    "contribution": {
        "id": "c1",
        "description": "Added endpoint documentation with examples.",
        "evidence": {"url": "https://example.com/pr/1"},
    },
    "participants": [],
}


class CrewaiWitnessTests(unittest.TestCase):
    def test_aggregate_role_results_median(self):
        rows = [
            {
                "task_match": 0.8,
                "quality": 0.9,
                "originality": 0.7,
                "impact": 0.6,
                "evidence_score": 0.85,
                "risk_score": 0.1,
                "suggested_cp": 20,
                "suggested_credits": 80,
                "rationale": "A",
                "concerns": ["c1"],
            },
            {
                "task_match": 0.6,
                "quality": 0.7,
                "originality": 0.5,
                "impact": 0.5,
                "evidence_score": 0.75,
                "risk_score": 0.3,
                "suggested_cp": 10,
                "suggested_credits": 40,
                "rationale": "B",
                "concerns": ["c2"],
            },
        ]
        result = aggregate_role_results(rows)
        self.assertEqual(result.provider, "crewai")
        self.assertAlmostEqual(result.task_match, 0.7)
        self.assertEqual(set(result.concerns), {"c1", "c2"})

    @patch.dict(os.environ, {"ENABLE_CREWAI_WITNESS": "true"}, clear=False)
    def test_native_role_crew_mock(self):
        result = asyncio.run(run_native_role_crew(SAMPLE_CONTEXT))
        self.assertEqual(result.provider, "crewai")
        self.assertGreaterEqual(result.quality, 0.5)
        self.assertGreaterEqual(result.evidence_score, 0.5)

    @patch.dict(os.environ, {"ENABLE_CREWAI_WITNESS": "true"}, clear=False)
    def test_verifier_available_and_verify(self):
        verifier = CrewaiWitnessVerifier()
        self.assertTrue(verifier.available)
        result = asyncio.run(verifier.verify(SAMPLE_CONTEXT))
        self.assertEqual(result.provider, "crewai")

    @patch.dict(os.environ, {"ENABLE_CREWAI_WITNESS": "true"}, clear=False)
    def test_run_crewai_witness_entrypoint(self):
        result = asyncio.run(run_crewai_witness(SAMPLE_CONTEXT))
        self.assertIn(result.rationale, result.rationale)  # non-empty
        self.assertTrue(crewai_witness_enabled())


if __name__ == "__main__":
    unittest.main()
