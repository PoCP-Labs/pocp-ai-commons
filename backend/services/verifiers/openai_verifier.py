import json
import os

import httpx

from services.verifiers.base import BaseVerifier, VerifierResult


class OpenAIVerifier(BaseVerifier):
    provider_name = "openai"

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def verify(self, context: dict) -> VerifierResult:
        if not self.available:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        prompt = build_verifier_prompt(context)
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are an AI advisory verifier for PoCP AI Commons. Return JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        return normalize_result(self.provider_name, self.model, data)


def build_verifier_prompt(context: dict) -> str:
    return f"""
You are Clarion-0, an AI advisory verifier for PoCP AI Commons.
You are a Reviewer Assistant / Contribution Verifier Agent.
You do not approve or reject contributions. You only provide structured advisory review for human reviewers.

Evaluate:
- task match
- quality
- originality
- impact
- evidence credibility
- risk
- suggested CP
- suggested AI Credits

Clarion-0 review guardrails:
- Separate evidence from interpretation.
- Name uncertainty plainly.
- Do not inflate rewards when evidence is weak.
- Flag plagiarism, spam, unsafe content, unverifiable claims, license issues, and self-review risks.
- Keep final authority with human reviewers.

Return JSON only:
{{
  "task_match": 0.0,
  "quality": 0.0,
  "originality": 0.0,
  "impact": 0.0,
  "evidence_score": 0.0,
  "risk_score": 0.0,
  "suggested_cp": 0,
  "suggested_credits": 0,
  "rationale": "string",
  "concerns": ["string"],
  "reviewer_questions": ["string"],
  "proof_draft": {{
    "summary": "string",
    "evidence": ["string"],
    "recommended_status": "needs_human_review"
  }}
}}

Context:
{json.dumps(context, ensure_ascii=False, indent=2)}
"""


def _clamp(value, default=0.0):
    try:
        return max(0.0, min(float(value), 1.0))
    except Exception:
        return default


def _non_negative_float(value, default=0.0):
    try:
        return max(0.0, float(value))
    except Exception:
        return default


def normalize_result(provider: str, model: str, data: dict) -> VerifierResult:
    return VerifierResult(
        provider=provider,
        model=model,
        task_match=_clamp(data.get("task_match"), 0.5),
        quality=_clamp(data.get("quality"), 0.5),
        originality=_clamp(data.get("originality"), 0.5),
        impact=_clamp(data.get("impact"), 0.5),
        evidence_score=_clamp(data.get("evidence_score"), 0.5),
        risk_score=_clamp(data.get("risk_score"), 0.5),
        suggested_cp=_non_negative_float(data.get("suggested_cp")),
        suggested_credits=_non_negative_float(data.get("suggested_credits")),
        rationale=str(data.get("rationale") or "No rationale provided."),
        concerns=list(data.get("concerns") or []),
    )
