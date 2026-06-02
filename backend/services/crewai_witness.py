"""CrewAI-style multi-agent witness — native role crew + optional CrewAI library + HTTP gateway."""

from __future__ import annotations

import asyncio
import json
import os
from functools import lru_cache
from pathlib import Path
from statistics import median
from typing import Any

import httpx
import yaml

from services.ai_chat import generate_ai_reply
from services.verifiers.base import VerifierResult
from services.llm_language import verifier_system_prompt
from services.verifiers.openai_verifier import build_verifier_prompt, normalize_result

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "crewai_witness.yaml"


def crewai_witness_enabled() -> bool:
    return os.getenv("ENABLE_CREWAI_WITNESS", "false").lower() in ("true", "1", "yes", "on")


def crewai_library_enabled() -> bool:
    return (
        crewai_witness_enabled()
        and os.getenv("ENABLE_CREWAI_WITNESS_USE_LIBRARY", "false").lower()
        in ("true", "1", "yes", "on")
    )


def crewai_package_available() -> bool:
    try:
        import crewai  # noqa: F401

        return True
    except ImportError:
        return False


@lru_cache(maxsize=1)
def load_crewai_witness_config() -> dict[str, Any]:
    if not _CONFIG_PATH.exists():
        return {"agents": []}
    with _CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
    return {}


def _mock_role_review(agent: dict[str, Any], context: dict) -> dict[str, Any]:
    """Deterministic per-role scores for mock/demo mode without paid LLM keys."""
    description = (context.get("contribution") or {}).get("description") or ""
    evidence = (context.get("contribution") or {}).get("evidence") or {}
    has_evidence = bool(evidence)
    length_score = min(len(description) / 800, 1.0)
    role_id = agent.get("id", "reviewer")

    base_quality = max(0.55, min(0.72 + length_score * 0.18, 0.92))
    base_evidence = 0.88 if has_evidence else 0.28
    base_risk = 0.12 if has_evidence else 0.52

    if role_id == "evidence_analyst":
        quality = base_quality * 0.95
        evidence_score = min(base_evidence + 0.05, 1.0)
        risk_score = base_risk
        concerns = [] if has_evidence else ["Evidence Analyst: missing or weak evidence."]
    elif role_id == "quality_reviewer":
        quality = min(base_quality + 0.04, 1.0)
        evidence_score = base_evidence
        risk_score = max(base_risk - 0.05, 0.0)
        concerns = [] if length_score > 0.2 else ["Quality Reviewer: description too thin."]
    else:
        quality = base_quality
        evidence_score = base_evidence
        risk_score = base_risk
        avg = (quality + base_evidence + 0.78 + 0.68) / 4
        suggested_cp = round(avg * 24, 2)
        suggested_credits = round(avg * 96, 2)
        return {
            "task_match": 0.79,
            "quality": quality,
            "originality": 0.68,
            "impact": 0.62,
            "evidence_score": evidence_score,
            "risk_score": risk_score,
            "suggested_cp": suggested_cp,
            "suggested_credits": suggested_credits,
            "rationale": f"{agent.get('role')}: synthesized reward advisory from crew signals.",
            "concerns": [] if has_evidence else ["Reward Advisor: low confidence without evidence."],
        }

    avg = (quality + evidence_score + 0.78 + 0.66) / 4
    return {
        "task_match": 0.78,
        "quality": quality,
        "originality": 0.67,
        "impact": 0.61,
        "evidence_score": evidence_score,
        "risk_score": risk_score,
        "suggested_cp": round(avg * 22, 2),
        "suggested_credits": round(avg * 88, 2),
        "rationale": f"{agent.get('role')}: advisory review for human finalization.",
        "concerns": concerns,
    }


async def _llm_role_review(agent: dict[str, Any], context: dict) -> dict[str, Any]:
    provider = os.getenv("CREWAI_WITNESS_LLM_PROVIDER", "mock").lower()
    model = os.getenv("CREWAI_WITNESS_MODEL") or None
    prompt = build_verifier_prompt(context)
    system = verifier_system_prompt(
        role_label=f"{agent.get('role')} in a PoCP witness crew (goal: {agent.get('goal')})"
    )
    if provider == "mock":
        return _mock_role_review(agent, context)

    content, _, used_model = await generate_ai_reply(prompt, provider=provider, model=model, system_content=system)
    parsed = _extract_json(content)
    if not parsed:
        parsed = _mock_role_review(agent, context)
        parsed["concerns"] = list(parsed.get("concerns") or []) + ["LLM JSON parse fallback used."]
    parsed["_model"] = used_model
    return parsed


def aggregate_role_results(
    role_results: list[dict[str, Any]],
    *,
    provider: str = "crewai",
    model: str = "native-role-crew",
) -> VerifierResult:
    if not role_results:
        raise ValueError("No role results to aggregate")

    numeric_keys = (
        "task_match",
        "quality",
        "originality",
        "impact",
        "evidence_score",
        "risk_score",
        "suggested_cp",
        "suggested_credits",
    )
    aggregated: dict[str, Any] = {}
    for key in numeric_keys:
        values = [float(r[key]) for r in role_results if key in r]
        aggregated[key] = median(values) if values else 0.5

    concerns: list[str] = []
    for row in role_results:
        for item in row.get("concerns") or []:
            if item and item not in concerns:
                concerns.append(str(item))

    rationales = [str(r.get("rationale") or "").strip() for r in role_results if r.get("rationale")]
    synthesized = " | ".join(rationales[:3]) if rationales else "Multi-agent crew consensus."

    return normalize_result(
        provider,
        model,
        {
            **aggregated,
            "rationale": synthesized,
            "concerns": concerns,
        },
    )


async def run_native_role_crew(context: dict) -> VerifierResult:
    """Sequential role-based review without the crewai pip package."""
    config = load_crewai_witness_config()
    agents = [a for a in config.get("agents") or [] if isinstance(a, dict)]
    if not agents:
        raise RuntimeError("crewai_witness.yaml has no agents")

    role_results: list[dict[str, Any]] = []
    model_label = "native-role-crew"
    for agent in agents:
        row = await _llm_role_review(agent, context)
        if row.get("_model"):
            model_label = str(row["_model"])
        role_results.append(row)

    return aggregate_role_results(role_results, provider="crewai", model=model_label)


def _run_crewai_library_sync(context: dict) -> VerifierResult:
    from crewai import Agent, Crew, Process, Task

    config = load_crewai_witness_config()
    agents_cfg = [a for a in config.get("agents") or [] if isinstance(a, dict)]
    prompt = build_verifier_prompt(context)
    crew_agents = []
    tasks = []
    for spec in agents_cfg:
        agent = Agent(
            role=str(spec.get("role") or "Reviewer"),
            goal=str(spec.get("goal") or "Review contribution"),
            backstory=f"PoCP witness crew member ({spec.get('id')}). Advisory only.",
            verbose=False,
        )
        crew_agents.append(agent)
        tasks.append(
            Task(
                description=(
                    f"{spec.get('goal')}\n\nReturn JSON only with verifier scores.\n\n{prompt}"
                ),
                expected_output="JSON verifier scores",
                agent=agent,
            )
        )

    crew = Crew(agents=crew_agents, tasks=tasks, process=Process.sequential, verbose=False)
    raw = crew.kickoff(inputs={"context": context})
    text = str(raw)
    parsed = _extract_json(text)
    if parsed:
        return normalize_result("crewai", "crewai-library", parsed)

    # Library returned prose — treat as single synthesized review
    return normalize_result(
        "crewai",
        "crewai-library",
        {
            "task_match": 0.75,
            "quality": 0.72,
            "originality": 0.65,
            "impact": 0.6,
            "evidence_score": 0.7,
            "risk_score": 0.25,
            "suggested_cp": 18,
            "suggested_credits": 72,
            "rationale": text[:500],
            "concerns": [],
        },
    )


async def run_crewai_library_crew(context: dict) -> VerifierResult:
    if not crewai_package_available():
        raise RuntimeError("crewai package not installed")
    return await asyncio.to_thread(_run_crewai_library_sync, context)


async def run_http_crewai_witness(context: dict) -> VerifierResult:
    url = os.getenv("CREWAI_WITNESS_URL", "").strip().rstrip("/")
    if not url:
        raise RuntimeError("CREWAI_WITNESS_URL not configured")

    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("CREWAI_WITNESS_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    timeout = float(os.getenv("CREWAI_WITNESS_TIMEOUT_SECONDS", "120"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json={"context": context, "crew": load_crewai_witness_config()})
        resp.raise_for_status()
        data = resp.json()

    if isinstance(data, list):
        return aggregate_role_results(data, provider="crewai", model="http-crew")
    if "provider" in data and "quality" in data:
        return VerifierResult.model_validate(data)
    return normalize_result("crewai", str(data.get("model") or "http-crew"), data)


async def run_crewai_witness(context: dict) -> VerifierResult:
    """Preferred path: HTTP gateway → CrewAI library → native role crew."""
    if os.getenv("CREWAI_WITNESS_URL", "").strip():
        return await run_http_crewai_witness(context)
    if crewai_library_enabled() and crewai_package_available():
        return await run_crewai_library_crew(context)
    return await run_native_role_crew(context)


def crewai_witness_runtime_mode() -> str:
    if os.getenv("CREWAI_WITNESS_URL", "").strip():
        return "http"
    if crewai_library_enabled() and crewai_package_available():
        return "library"
    return "native"
