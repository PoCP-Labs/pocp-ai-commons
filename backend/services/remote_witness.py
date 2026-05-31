"""Execute a single-provider witness for local or peer compute nodes."""

from __future__ import annotations

from services.ai_verify_service import ai_verify_service
from services.verifiers.base import VerifierResult
from services.verifiers.mock_verifier import MockVerifier


async def run_witness(context: dict, *, provider: str = "mock") -> VerifierResult:
    task = context.get("task") or {}
    contribution = context.get("contribution") or {}
    participants = context.get("participants") or []

    if provider in ("simulated", "mock"):
        result = await MockVerifier().verify(context)
        return result

    rubric = await ai_verify_service(
        task_title=task.get("title"),
        task_description=task.get("description"),
        contribution_description=contribution.get("description"),
        evidence=contribution.get("evidence"),
        participants=participants,
        provider=provider,
    )
    return VerifierResult(
        provider=rubric.provider,
        model=rubric.model,
        task_match=rubric.task_match,
        quality=rubric.quality,
        originality=rubric.originality,
        impact=rubric.impact,
        evidence_score=rubric.evidence_score,
        risk_score=rubric.risk_score,
        suggested_cp=rubric.suggested_cp,
        suggested_credits=rubric.suggested_credits,
        rationale=rubric.feedback,
        concerns=list(rubric.concerns),
    )
