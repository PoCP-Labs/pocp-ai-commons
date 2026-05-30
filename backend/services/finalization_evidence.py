"""Maestro-style evidence rows for finalization decisions."""

from __future__ import annotations

from typing import Any


def build_witness_evidence(consensus: dict[str, Any]) -> list[dict[str, Any]]:
    """Map verifier provider_results to witnessed evidence rows."""
    rows: list[dict[str, Any]] = []
    for item in consensus.get("provider_results") or []:
        provider = item.get("provider") or item.get("model_provider") or "unknown"
        quality = float(item.get("quality") or 0)
        risk = float(item.get("risk_score") or 1)
        passed = risk <= 0.5 and quality >= 0.6
        rows.append(
            {
                "kind": "witnessed-by-verifier",
                "source": provider,
                "quality": quality,
                "risk_score": risk,
                "passed": passed,
                "suggested_cp": item.get("suggested_cp"),
            }
        )
    if consensus.get("passed") is not None:
        rows.append(
            {
                "kind": "witnessed-by-consensus",
                "source": "multi_consensus",
                "passed": bool(consensus.get("passed")),
                "avg_score": consensus.get("avg_score"),
                "avg_risk": consensus.get("avg_risk"),
                "disagreement_high": consensus.get("disagreement_high"),
            }
        )
    return rows
