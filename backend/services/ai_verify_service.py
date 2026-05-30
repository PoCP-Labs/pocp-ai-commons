"""Single-provider AI verification for manual /verify when score=0."""

from pydantic import BaseModel, Field

from services.verifiers.base import BaseVerifier, VerifierResult
from services.verifiers.deepseek_verifier import DeepSeekVerifier
from services.verifiers.mock_verifier import MockVerifier
from services.verifiers.openai_verifier import OpenAIVerifier


class AiVerifyRubric(BaseModel):
    provider: str
    model: str
    score: float = Field(ge=0.0, le=1.0)
    feedback: str
    task_match: float = Field(ge=0.0, le=1.0)
    quality: float = Field(ge=0.0, le=1.0)
    originality: float = Field(ge=0.0, le=1.0)
    impact: float = Field(ge=0.0, le=1.0)
    evidence_score: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    suggested_cp: float = Field(ge=0.0)
    suggested_credits: float = Field(ge=0.0)
    concerns: list[str] = Field(default_factory=list)

    @classmethod
    def from_verifier_result(cls, result: VerifierResult) -> "AiVerifyRubric":
        score = (
            result.task_match
            + result.quality
            + result.originality
            + result.impact
            + result.evidence_score
        ) / 5
        return cls(
            provider=result.provider,
            model=result.model,
            score=round(score, 4),
            feedback=result.rationale,
            task_match=result.task_match,
            quality=result.quality,
            originality=result.originality,
            impact=result.impact,
            evidence_score=result.evidence_score,
            risk_score=result.risk_score,
            suggested_cp=result.suggested_cp,
            suggested_credits=result.suggested_credits,
            concerns=list(result.concerns),
        )


def _resolve_provider(provider: str) -> BaseVerifier:
    normalized = (provider or "simulated").lower()
    if normalized in ("simulated", "mock"):
        return MockVerifier()
    if normalized == "deepseek":
        return DeepSeekVerifier()
    if normalized == "openai":
        return OpenAIVerifier()
    return MockVerifier()


async def ai_verify_service(
    *,
    task_title: str | None = None,
    task_description: str | None = None,
    contribution_description: str | None = None,
    evidence: dict | None = None,
    participants: list[dict] | None = None,
    provider: str = "simulated",
) -> AiVerifyRubric:
    context = {
        "task": {
            "title": task_title,
            "description": task_description,
        },
        "contribution": {
            "description": contribution_description,
            "evidence": evidence or {},
        },
        "participants": participants or [],
    }

    verifier = _resolve_provider(provider)
    if hasattr(verifier, "available") and not verifier.available:
        verifier = MockVerifier()
    try:
        result = await verifier.verify(context)
    except Exception:
        result = await MockVerifier().verify(context)
    return AiVerifyRubric.from_verifier_result(result)
