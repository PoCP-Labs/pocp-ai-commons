"""Clarion-0 heuristic verifier adapter."""

from services.clarion import score_context_for_verifier
from services.verifiers.base import BaseVerifier, VerifierResult


class ClarionVerifier(BaseVerifier):
    provider_name = "clarion-0"

    @property
    def available(self) -> bool:
        return True

    async def verify(self, context: dict) -> VerifierResult:
        scored = score_context_for_verifier(context)
        return VerifierResult(
            provider="clarion-0",
            model="clarion-heuristic-v0",
            task_match=scored["task_match"],
            quality=scored["quality"],
            originality=scored["originality"],
            impact=scored["impact"],
            evidence_score=scored["evidence_score"],
            risk_score=scored["risk_score"],
            suggested_cp=scored["suggested_cp"],
            suggested_credits=scored["suggested_credits"],
            rationale=scored["rationale"],
            concerns=scored["concerns"],
        )
