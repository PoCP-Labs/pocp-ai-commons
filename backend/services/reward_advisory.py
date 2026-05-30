"""Parse AI verifier consensus into human-facing reward advisory."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from models.contribution import AiVerifierResult, ContributionEvent


def _parse_feedback(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def build_reward_advisory(db: Session, contribution: ContributionEvent) -> dict:
    """Surface suggested CP/BC from multi_consensus and per-provider results."""
    results = (
        db.query(AiVerifierResult)
        .filter(AiVerifierResult.contribution_id == contribution.id)
        .order_by(AiVerifierResult.created_at.desc())
        .all()
    )

    consensus_row = next((r for r in results if r.model_provider == "multi_consensus"), None)
    consensus = _parse_feedback(consensus_row.feedback) if consensus_row else None

    provider_rows = []
    for row in results:
        if row.model_provider == "multi_consensus":
            continue
        payload = _parse_feedback(row.feedback)
        if payload:
            provider_rows.append(
                {
                    "provider": row.model_provider,
                    "score": row.score,
                    "passed": row.passed,
                    "suggested_cp": payload.get("suggested_cp"),
                    "suggested_credits": payload.get("suggested_credits"),
                    "quality": payload.get("quality"),
                    "risk_score": payload.get("risk_score"),
                }
            )

    advisory = {
        "contribution_id": contribution.id,
        "status": contribution.status.value,
        "source": "ai_verifier_consensus",
        "compat": "meritocrab-advisory-v0",
        "note": (
            "Advisory only — actual CP/BC issuance follows pocp_rewards.yaml on human approval."
        ),
        "consensus": consensus,
        "providers": provider_rows,
    }

    if consensus:
        advisory["recommended"] = {
            "cp": consensus.get("suggested_cp"),
            "ai_credits": consensus.get("suggested_credits"),
            "avg_score": consensus.get("avg_score"),
            "avg_risk": consensus.get("avg_risk"),
            "disagreement_high": consensus.get("disagreement_high"),
            "passed": consensus.get("passed"),
        }
    elif results:
        advisory["recommended"] = {
            "cp": None,
            "ai_credits": None,
            "avg_score": results[0].score,
            "note": "No multi_consensus row; showing latest verifier score only.",
        }

    return advisory
