from services.verifiers.base import BaseVerifier, VerifierResult


class MockVerifier(BaseVerifier):
    provider_name = "mock"

    async def verify(self, context: dict) -> VerifierResult:
        description = context.get("contribution", {}).get("description") or ""
        evidence = context.get("contribution", {}).get("evidence") or {}
        has_evidence = bool(evidence)
        length_score = min(len(description) / 800, 1.0)
        quality = max(0.55, min(0.75 + length_score * 0.2, 0.95))
        evidence_score = 0.85 if has_evidence else 0.25
        risk = 0.15 if has_evidence else 0.55
        base_score = (quality + evidence_score + 0.8 + 0.7) / 4
        return VerifierResult(
            provider="mock",
            model="mock-verifier-v0",
            task_match=0.8,
            quality=quality,
            originality=0.7,
            impact=0.65,
            evidence_score=evidence_score,
            risk_score=risk,
            suggested_cp=round(base_score * 25, 2),
            suggested_credits=round(base_score * 100, 2),
            rationale="Mock verifier generated a deterministic advisory score for local demo mode.",
            concerns=[] if has_evidence else ["Evidence is weak or missing."],
        )
