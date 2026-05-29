from pydantic import BaseModel, Field


class VerifierResult(BaseModel):
    provider: str
    model: str
    task_match: float = Field(ge=0.0, le=1.0)
    quality: float = Field(ge=0.0, le=1.0)
    originality: float = Field(ge=0.0, le=1.0)
    impact: float = Field(ge=0.0, le=1.0)
    evidence_score: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    suggested_cp: float = Field(ge=0.0)
    suggested_credits: float = Field(ge=0.0)
    rationale: str
    concerns: list[str] = []


class BaseVerifier:
    provider_name = "base"

    async def verify(self, context: dict) -> VerifierResult:
        raise NotImplementedError
