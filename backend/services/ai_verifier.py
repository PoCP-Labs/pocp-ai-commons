"""AI Verifier — real LLM-based contribution verification.

GENESIS.md §6:
  "AI may advise. AI may score. AI may surface risk.
   AI may summarize evidence. AI may not be the final judge."

This module makes AI verification real:
1. Constructs a verification prompt from contribution data
2. Calls an LLM API (DeepSeek, OpenAI, or local Ollama)
3. Parses structured rubric output
4. Returns advisory score + feedback + risk flags

The AI verdict is ADVISORY ONLY. Human review is still required.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from config import AI_VERIFIER_MODEL, AI_VERIFIER_THRESHOLD

logger = logging.getLogger("pocp")


@dataclass
class VerificationRubric:
    """Structured AI verification result."""

    score: float  # 0.0 - 1.0 overall score
    task_match: float  # How well the contribution matches the task
    quality: float  # Quality of the contribution content
    originality: float  # Whether the contribution appears original
    evidence_score: float  # How well the evidence supports the claim
    risk_flags: list[str]  # Potential issues (plagiarism, spam, etc.)
    suggested_cp: float  # Suggested CP reward
    suggested_credits: float  # Suggested AI Credits reward
    feedback: str  # Human-readable rationale
    passed: bool  # Whether it meets the threshold


VERIFICATION_PROMPT = """You are an AI Verifier for the Proof of Contribution Protocol (PoCP).

Your role is ADVISORY ONLY. You assess contributions and provide recommendations.
The final decision always rests with human reviewers.

## Contribution Details
Task: {task_title}
Task Description: {task_description}
Contribution Type: {contribution_type}
Contribution Description: {contribution_description}
Evidence: {evidence}
Participants: {participants}

## Verification Rubric
Evaluate the contribution on the following dimensions (0.0 - 1.0):

1. **Task Match** (0-1): How well does the contribution address the task?
2. **Quality** (0-1): Is the contribution well-crafted and substantive?
3. **Originality** (0-1): Does the contribution appear to be original work?
4. **Evidence Score** (0-1): How well does the evidence support the claim?

## Risk Assessment
Identify any potential risks:
- Plagiarism indicators
- Spam or low-effort content
- Duplicate contribution
- Evidence credibility issues
- Other red flags

## Reward Suggestion
Based on your assessment, suggest:
- CP (Contribution Points): 0-50 scale
- AI Credits: 0-300 scale

## Response Format
Return a JSON object with this exact structure:
{{
  "task_match": 0.85,
  "quality": 0.80,
  "originality": 0.90,
  "evidence_score": 0.75,
  "overall_score": 0.83,
  "risk_flags": ["flag1", "flag2"],
  "suggested_cp": 25,
  "suggested_credits": 150,
  "feedback": "Human-readable summary of your assessment."
}}

Only return valid JSON. No markdown, no explanation outside the JSON."""


def build_verification_prompt(
    task_title: str,
    task_description: str,
    contribution_type: str,
    contribution_description: str,
    evidence: dict,
    participants: list[dict],
) -> str:
    """Build the verification prompt from contribution data."""
    return VERIFICATION_PROMPT.format(
        task_title=task_title or "N/A",
        task_description=task_description or "N/A",
        contribution_type=contribution_type,
        contribution_description=contribution_description or "N/A",
        evidence=json.dumps(evidence, indent=2) if evidence else "No evidence provided",
        participants=json.dumps(participants, indent=2) if participants else "No participants",
    )


def parse_rubric(response_text: str) -> VerificationRubric:
    """Parse LLM response into a VerificationRubric."""
    # Try to extract JSON from the response
    json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
    if not json_match:
        raise ValueError(f"Could not parse JSON from AI response: {response_text[:200]}")

    data = json.loads(json_match.group())

    overall = data.get("overall_score", 0.0)
    return VerificationRubric(
        score=round(min(1.0, max(0.0, float(overall))), 2),
        task_match=round(min(1.0, max(0.0, float(data.get("task_match", 0.0)))), 2),
        quality=round(min(1.0, max(0.0, float(data.get("quality", 0.0)))), 2),
        originality=round(min(1.0, max(0.0, float(data.get("originality", 0.0)))), 2),
        evidence_score=round(min(1.0, max(0.0, float(data.get("evidence_score", 0.0)))), 2),
        risk_flags=data.get("risk_flags", []),
        suggested_cp=round(float(data.get("suggested_cp", 10)), 2),
        suggested_credits=round(float(data.get("suggested_credits", 50)), 2),
        feedback=data.get("feedback", "AI verification completed."),
        passed=overall >= AI_VERIFIER_THRESHOLD,
    )


async def verify_with_deepseek(
    prompt: str,
    api_key: str,
    model: str = "deepseek-chat",
) -> str:
    """Call DeepSeek API for contribution verification."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an AI Verifier for PoCP. Return ONLY valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 1000,
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


async def verify_with_openai(
    prompt: str,
    api_key: str,
    model: str = "gpt-4o-mini",
) -> str:
    """Call OpenAI API for contribution verification."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an AI Verifier for PoCP. Return ONLY valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 1000,
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


async def verify_with_ollama(
    prompt: str,
    model: str = "llama3.2",
    base_url: str = "http://localhost:11434",
) -> str:
    """Call local Ollama instance for contribution verification."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an AI Verifier for PoCP. Return ONLY valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.1},
            },
        )
        response.raise_for_status()
        return response.json()["message"]["content"]


async def run_ai_verification(
    task_title: str,
    task_description: str,
    contribution_type: str,
    contribution_description: str,
    evidence: dict,
    participants: list[dict],
    provider: str = AI_VERIFIER_MODEL,
    api_key: Optional[str] = None,
) -> VerificationRubric:
    """Run AI verification on a contribution.

    Supports multiple LLM providers:
    - deepseek (DeepSeek API)
    - openai (OpenAI API)
    - ollama (local Ollama instance)
    - simulated (fallback with deterministic scoring)

    The result is ADVISORY ONLY. Human review is still required.
    """
    prompt = build_verification_prompt(
        task_title,
        task_description,
        contribution_type,
        contribution_description,
        evidence,
        participants,
    )

    try:
        if provider == "deepseek" and api_key:
            response = await verify_with_deepseek(prompt, api_key)
        elif provider == "openai" and api_key:
            response = await verify_with_openai(prompt, api_key)
        elif provider == "ollama":
            response = await verify_with_ollama(prompt)
        else:
            # Fallback to simulated verification
            response = _simulated_verification(
                contribution_description, evidence, participants
            )

        rubric = parse_rubric(response)
        logger.info(
            f"AI verification completed: provider={provider} "
            f"score={rubric.score} passed={rubric.passed}"
        )
        return rubric

    except Exception as e:
        logger.error(f"AI verification failed, falling back to simulated: {e}")
        # Fallback to simulated verification on any error
        response = _simulated_verification(
            contribution_description, evidence, participants
        )
        return parse_rubric(response)


def _simulated_verification(
    description: str,
    evidence: dict,
    participants: list[dict],
) -> str:
    """Generate a simulated AI verification response.

    This is used when no real LLM API is available.
    It provides deterministic but reasonable scoring based on contribution metadata.
    """
    has_url = bool(evidence.get("url"))
    has_hash = bool(evidence.get("content_hash"))
    has_content = bool(evidence.get("content_preview") or evidence.get("content"))
    desc_length = len(description or "")
    num_participants = len(participants)

    # Score based on evidence quality
    evidence_score = 0.0
    if has_url:
        evidence_score += 0.3
    if has_hash:
        evidence_score += 0.3
    if has_content:
        evidence_score += 0.2
    if desc_length > 50:
        evidence_score += 0.2
    evidence_score = min(1.0, evidence_score)

    # Other dimensions (simulated — all decent for valid submissions)
    task_match = min(1.0, 0.7 + (desc_length / 200))
    quality = min(1.0, 0.6 + (desc_length / 300))
    originality = 0.8  # Assume original for now

    overall = round(
        (task_match * 0.25 + quality * 0.25 + originality * 0.2 + evidence_score * 0.3),
        2,
    )

    # Reward suggestions based on quality
    suggested_cp = round(overall * 30, 0)
    suggested_credits = round(overall * 200, 0)

    risk_flags = []
    if desc_length < 20:
        risk_flags.append("Very short description — may be low effort")
    if not evidence:
        risk_flags.append("No evidence provided")
    if num_participants == 0:
        risk_flags.append("No participants attributed")

    return json.dumps({
        "task_match": round(task_match, 2),
        "quality": round(quality, 2),
        "originality": round(originality, 2),
        "evidence_score": round(evidence_score, 2),
        "overall_score": overall,
        "risk_flags": risk_flags,
        "suggested_cp": suggested_cp,
        "suggested_credits": suggested_credits,
        "feedback": (
            f"AI advisory assessment: score {overall}/1.0. "
            f"Task match: {task_match}, Quality: {quality}, "
            f"Originality: {originality}, Evidence: {evidence_score}. "
            f"{'No significant risk flags.' if not risk_flags else 'Risk flags: ' + '; '.join(risk_flags)}"
        ),
    })
