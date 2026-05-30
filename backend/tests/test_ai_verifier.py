"""Tests for the real AI Verifier service.

GENESIS.md §6: "AI is a witness, not a ruler."
The AI verifier analyzes contributions and provides advisory scores.
"""

import asyncio
import json

from services.ai_verifier import (
    VerificationRubric,
    build_verification_prompt,
    parse_rubric,
    _simulated_verification,
    run_ai_verification,
)


class TestBuildVerificationPrompt:
    """Test that verification prompts include all required context."""

    def test_prompt_includes_task_info(self):
        prompt = build_verification_prompt(
            task_title="Write R Tutorial",
            task_description="Create 5 R exercises",
            contribution_type="knowledge",
            contribution_description="I wrote 5 exercises about matrix operations",
            evidence={"url": "https://example.com"},
            participants=[{"entity_id": "abc", "role": "creator", "weight": 1.0}],
        )
        assert "Write R Tutorial" in prompt
        assert "Create 5 R exercises" in prompt

    def test_prompt_includes_evidence(self):
        prompt = build_verification_prompt(
            task_title="Test",
            task_description="Test",
            contribution_type="code",
            contribution_description="Fixed a bug",
            evidence={"url": "https://github.com/pull/123", "content_hash": "sha256:abc"},
            participants=[],
        )
        assert "https://github.com/pull/123" in prompt
        assert "sha256:abc" in prompt

    def test_prompt_handles_missing_data(self):
        prompt = build_verification_prompt(
            task_title="",
            task_description="",
            contribution_type="knowledge",
            contribution_description="",
            evidence={},
            participants=[],
        )
        assert "N/A" in prompt  # Missing fields shown as N/A


class TestParseRubric:
    """Test parsing of LLM responses into structured rubrics."""

    def test_parses_valid_json(self):
        response = json.dumps({
            "task_match": 0.85,
            "quality": 0.80,
            "originality": 0.90,
            "evidence_score": 0.75,
            "overall_score": 0.83,
            "risk_flags": ["short description"],
            "suggested_cp": 25,
            "suggested_credits": 150,
            "feedback": "Good contribution overall.",
        })
        rubric = parse_rubric(response)
        assert rubric.score == 0.83
        assert rubric.task_match == 0.85
        assert rubric.quality == 0.80
        assert rubric.originality == 0.90
        assert rubric.evidence_score == 0.75
        assert "short description" in rubric.risk_flags
        assert rubric.suggested_cp == 25
        assert rubric.suggested_credits == 150
        assert "Good contribution" in rubric.feedback

    def test_parses_json_with_surrounding_text(self):
        response = "Here is my assessment:\n\n```json\n" + json.dumps({
            "task_match": 0.7,
            "quality": 0.6,
            "originality": 0.8,
            "evidence_score": 0.5,
            "overall_score": 0.65,
            "risk_flags": [],
            "suggested_cp": 15,
            "suggested_credits": 80,
            "feedback": "Decent work.",
        }) + "\n```\n\nHope this helps!"
        rubric = parse_rubric(response)
        assert rubric.score == 0.65

    def test_score_clamped_to_range(self):
        response = json.dumps({
            "task_match": 1.5,  # Invalid — should be clamped
            "quality": -0.2,
            "originality": 0.8,
            "evidence_score": 0.9,
            "overall_score": 1.5,  # Invalid — should be clamped to 1.0
            "risk_flags": [],
            "suggested_cp": 10,
            "suggested_credits": 50,
            "feedback": "Test.",
        })
        rubric = parse_rubric(response)
        assert rubric.score <= 1.0
        assert rubric.task_match <= 1.0
        assert rubric.quality >= 0.0


class TestSimulatedVerification:
    """Test the simulated verification fallback."""

    def test_good_contribution_gets_high_score(self):
        response = _simulated_verification(
            description="I created comprehensive R matrix operation exercises with examples, practice questions, and detailed solutions covering matrix creation, indexing, multiplication, and transpose operations.",
            evidence={
                "url": "https://example.com/r-exercises",
                "content_hash": "sha256:abc123",
                "content_preview": "Exercise 1: Create a 3x3 matrix...",
            },
            participants=[{"entity_id": "abc", "role": "creator", "weight": 1.0}],
        )
        rubric = parse_rubric(response)
        assert rubric.score >= 0.5
        assert rubric.evidence_score >= 0.5
        assert rubric.suggested_cp >= 10
        assert rubric.suggested_credits >= 50

    def test_short_description_gets_lower_score(self):
        response = _simulated_verification(
            description="Fixed bug",
            evidence={},
            participants=[],
        )
        rubric = parse_rubric(response)
        assert len(rubric.risk_flags) >= 1  # Should flag short description

    def test_no_evidence_gets_risk_flag(self):
        response = _simulated_verification(
            description="Some contribution",
            evidence={},
            participants=[],
        )
        rubric = parse_rubric(response)
        assert any("evidence" in f.lower() or "no evidence" in f.lower() for f in rubric.risk_flags) or any("evidence" in rubric.feedback.lower())


class TestAIVerificationFlow:
    """Test the full AI verification flow (simulated mode)."""

    def test_simulated_verification_returns_rubric(self):
        async def _test():
            rubric = await run_ai_verification(
                task_title="Write R Tutorial",
                task_description="Create 5 exercises about matrix operations",
                contribution_type="knowledge",
                contribution_description="I wrote comprehensive exercises with solutions",
                evidence={"url": "https://example.com"},
                participants=[{"entity_id": "abc", "role": "creator", "weight": 1.0}],
                provider="simulated",
            )
            return rubric

        rubric = asyncio.get_event_loop().run_until_complete(_test())
        assert isinstance(rubric, VerificationRubric)
        assert 0.0 <= rubric.score <= 1.0
        assert isinstance(rubric.feedback, str)
        assert len(rubric.feedback) > 0
