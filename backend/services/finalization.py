"""Finalization policy — policy-bot rules + maestro verdict + OPA-style decision_id."""

from __future__ import annotations

import json
import os
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from sqlalchemy.orm import Session

from genesis import CLARION_0_ID
from models.contribution import ContributionEvent, ContributionStatus
from services.contribution import approve_contribution
from services.finalization_evidence import build_witness_evidence
from services.verdict import Verdict, compute_verdict

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "finalization_policy.yaml"

_DEFAULTS: dict[str, Any] = {
    "spec_version": "0.2",
    "policy_id": "entity_equal_auto_v1",
    "description": "Entity-equal auto-finalization — no human gate; witness quorum + policy delegate",
    "enabled": True,
    "auto_finalize_on_escalate": True,
    "default_finalizer_entity_id": CLARION_0_ID,
    "finalizer_role": "entity_delegate",
    "allowed_finalizer_entity_types": [
        "human",
        "agent",
        "llm",
        "skill",
        "tool",
        "dataset",
        "workflow",
        "organization",
        "community",
    ],
    "verdict_routing": {
        "pass": "PASS",
        "escalate": "ESCALATE",
        "fail": "FAIL",
        "block": "BLOCK",
    },
    "auto_finalize_when": {"all_of": ["witness_quorum", "cp_cap", "consensus_passed", "no_high_disagreement"]},
    "escalate_when": {"any_of": ["cp_over_cap", "high_disagreement"]},
    "rules": {
        "witness_quorum": {
            "min_witnesses": 1,
            "min_avg_score": 0.7,
            "max_avg_risk": 0.5,
        },
        "cp_cap": {"max_suggested_cp": 200},
        "cp_over_cap": {"max_suggested_cp": 200},
        "consensus_passed": {"require_passed": True},
        "no_high_disagreement": {"disallow_high_disagreement": True},
        "high_disagreement": {"trigger_on_high_disagreement": True},
    },
    # legacy flat quorum — merged into rules.witness_quorum when present
    "witness_quorum": {},
}

_DEFAULT_FINALIZER_TYPES = (
    "human",
    "agent",
    "llm",
    "skill",
    "tool",
    "dataset",
    "workflow",
    "organization",
    "community",
)


@lru_cache(maxsize=1)
def get_finalization_policy() -> dict[str, Any]:
    path = os.getenv("POCP_FINALIZATION_POLICY_PATH")
    config_path = Path(path) if path else _CONFIG_PATH
    if not config_path.exists():
        return dict(_DEFAULTS)
    with config_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    merged = dict(_DEFAULTS)
    merged.update({k: v for k, v in data.items() if k not in ("witness_quorum", "rules")})
    rules = dict(_DEFAULTS["rules"])
    if "rules" in data and isinstance(data["rules"], dict):
        for name, cfg in data["rules"].items():
            rules[name] = {**rules.get(name, {}), **cfg}
    # Legacy witness_quorum top-level keys fold into rules.witness_quorum
    legacy_wq = data.get("witness_quorum") or {}
    if legacy_wq:
        rules["witness_quorum"] = {**rules.get("witness_quorum", {}), **legacy_wq}
        merged["witness_quorum"] = rules["witness_quorum"]
    merged["rules"] = rules
    if "auto_finalize_when" in data:
        merged["auto_finalize_when"] = data["auto_finalize_when"]
    if "escalate_when" in data:
        merged["escalate_when"] = data["escalate_when"]
    if "verdict_routing" in data:
        merged["verdict_routing"] = {**_DEFAULTS["verdict_routing"], **data["verdict_routing"]}

    if os.getenv("POCP_PILOT_MODE", "").strip().lower() in ("true", "1", "yes", "on"):
        wq = merged["rules"].setdefault("witness_quorum", {})
        wq["min_distinct_witness_nodes"] = int(
            os.getenv("POCP_MIN_DISTINCT_WITNESS_NODES", "2")
        )
        if os.getenv("ENABLE_PEER_COMPUTE", "").strip().lower() in ("true", "1", "yes", "on"):
            wq["min_witnesses"] = max(int(wq.get("min_witnesses", 1)), 2)

    return merged


def clear_finalization_policy_cache() -> None:
    get_finalization_policy.cache_clear()


def new_decision_id() -> str:
    """OPA-style unique id for a finalization policy evaluation."""
    return str(uuid.uuid4())


def is_auto_finalization_enabled(policy: dict[str, Any] | None = None) -> bool:
    policy = policy or get_finalization_policy()
    env = os.getenv("ENABLE_AUTO_FINALIZATION", "").strip().lower()
    if env in ("true", "1", "yes", "on"):
        return True
    if env in ("false", "0", "no", "off"):
        return False
    return bool(policy.get("enabled", False))


def finalizer_entity_id(policy: dict[str, Any] | None = None) -> str:
    policy = policy or get_finalization_policy()
    return os.getenv("POCP_FINALIZER_ENTITY_ID") or policy.get("default_finalizer_entity_id") or CLARION_0_ID


def allowed_finalizer_entity_types(policy: dict[str, Any] | None = None) -> tuple[str, ...]:
    policy = policy or get_finalization_policy()
    raw = policy.get("allowed_finalizer_entity_types")
    if isinstance(raw, list) and raw:
        return tuple(str(t) for t in raw)
    return _DEFAULT_FINALIZER_TYPES


def validate_finalizer_entity(entity) -> None:
    entity_type = entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type)
    allowed = allowed_finalizer_entity_types()
    if entity_type not in allowed:
        raise ValueError(
            f"Finalizer entity type '{entity_type}' is not allowed under instance policy "
            f"(allowed: {', '.join(allowed)})"
        )


def _witness_pass_count(consensus: dict[str, Any]) -> int:
    passing = 0
    for item in consensus.get("provider_results") or []:
        quality = float(item.get("quality") or 0)
        risk = float(item.get("risk_score") or 1)
        if risk <= 0.5 and quality >= 0.6:
            passing += 1
    return passing


def _distinct_witness_nodes(consensus: dict[str, Any]) -> int:
    """Count distinct witness sources — peer:node_id vs local provider names."""
    nodes: set[str] = set()
    for item in consensus.get("provider_results") or []:
        provider = str(item.get("provider") or "")
        if not provider:
            continue
        if provider.startswith("peer:"):
            nodes.add(provider)
        else:
            nodes.add(f"local:{provider}")
    return len(nodes)


def witness_diversity_summary(consensus: dict[str, Any]) -> dict[str, Any]:
    providers = [str(p.get("provider")) for p in consensus.get("provider_results") or [] if p.get("provider")]
    return {
        "distinct_witness_nodes": _distinct_witness_nodes(consensus),
        "witness_providers": providers,
        "advisory_only": True,
    }


def _evaluate_named_rules(consensus: dict[str, Any], policy: dict[str, Any]) -> dict[str, bool]:
    """Policy-bot style named rule checks."""
    rules_cfg = policy.get("rules") or {}
    wq = rules_cfg.get("witness_quorum") or policy.get("witness_quorum") or {}
    witness_count = _witness_pass_count(consensus)
    distinct_nodes = _distinct_witness_nodes(consensus)
    min_distinct = int(wq.get("min_distinct_witness_nodes", 1))
    avg_score = float(consensus.get("avg_score") or 0)
    avg_risk = float(consensus.get("avg_risk") or 1)
    suggested_cp = float(consensus.get("suggested_cp") or 0)
    disagreement = bool(consensus.get("disagreement_high"))
    consensus_passed = bool(consensus.get("passed"))
    cp_cap = float((rules_cfg.get("cp_cap") or {}).get("max_suggested_cp", 200))

    checks: dict[str, bool] = {
        "auto_finalization_enabled": is_auto_finalization_enabled(policy),
        "witness_quorum": witness_count >= int(wq.get("min_witnesses", 1))
        and avg_score >= float(wq.get("min_avg_score", 0.7))
        and avg_risk <= float(wq.get("max_avg_risk", 0.5))
        and distinct_nodes >= min_distinct,
        "witness_diversity": distinct_nodes >= min_distinct,
        "cp_cap": suggested_cp <= cp_cap,
        "cp_over_cap": suggested_cp > cp_cap,
        "consensus_passed": consensus_passed
        if (rules_cfg.get("consensus_passed") or {}).get("require_passed", True)
        else True,
        "no_high_disagreement": not disagreement
        if (rules_cfg.get("no_high_disagreement") or {}).get("disallow_high_disagreement", True)
        else True,
        "high_disagreement": disagreement
        if (rules_cfg.get("high_disagreement") or {}).get("trigger_on_high_disagreement", True)
        else False,
        # legacy aliases used in tests
        "min_witnesses": witness_count >= int(wq.get("min_witnesses", 1)),
        "min_distinct_witness_nodes": distinct_nodes >= min_distinct,
        "min_avg_score": avg_score >= float(wq.get("min_avg_score", 0.7)),
        "max_avg_risk": avg_risk <= float(wq.get("max_avg_risk", 0.5)),
        "max_suggested_cp": suggested_cp <= cp_cap,
        "no_high_disagreement_legacy": not disagreement,
    }
    return checks


def evaluate_finalization_policy(
    consensus: dict[str, Any],
    policy: dict[str, Any] | None = None,
    *,
    decision_id: str | None = None,
) -> dict[str, Any]:
    """Evaluate policy-bot rules and return maestro-style verdict snapshot."""
    policy = policy or get_finalization_policy()
    checks = _evaluate_named_rules(consensus, policy)
    decision_id = decision_id or new_decision_id()

    auto_rule_names = (policy.get("auto_finalize_when") or {}).get("all_of") or [
        "witness_quorum",
        "cp_cap",
        "consensus_passed",
        "no_high_disagreement",
    ]
    auto_finalize_eligible = all(checks.get(name, False) for name in auto_rule_names)
    auto_finalize_eligible = auto_finalize_eligible and checks.get("auto_finalization_enabled", False)

    verdict = compute_verdict(
        consensus=consensus,
        checks=checks,
        auto_finalize_eligible=auto_finalize_eligible,
        policy=policy,
    )

    wq = (policy.get("rules") or {}).get("witness_quorum") or policy.get("witness_quorum") or {}
    witness_count = _witness_pass_count(consensus)

    return {
        "decision_id": decision_id,
        "policy_id": policy.get("policy_id"),
        "policy_version": policy.get("spec_version"),
        "policy_path": "pocp/finalization/evaluate",
        "mode": "witness_quorum",
        "verdict": verdict.value,
        "eligible": auto_finalize_eligible and verdict == Verdict.PASS,
        "checks": checks,
        "rules_evaluated": auto_rule_names,
        "witness_count": witness_count,
        "evidence": build_witness_evidence(consensus),
        "finalizer_entity_id": finalizer_entity_id(policy),
        "finalizer_role": policy.get("finalizer_role"),
        "consensus_summary": {
            "avg_score": float(consensus.get("avg_score") or 0),
            "avg_risk": float(consensus.get("avg_risk") or 1),
            "suggested_cp": float(consensus.get("suggested_cp") or 0),
            "disagreement_high": bool(consensus.get("disagreement_high")),
            "passed": bool(consensus.get("passed")),
        },
    }


def evaluate_witness_quorum(consensus: dict[str, Any], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Backward-compatible alias."""
    return evaluate_finalization_policy(consensus, policy)


def build_finalization_ledger_meta(
    evaluation: dict[str, Any],
    *,
    applied: bool,
) -> dict[str, Any]:
    return {
        "decision_id": evaluation.get("decision_id"),
        "verdict": evaluation.get("verdict"),
        "mode": evaluation.get("mode"),
        "applied": applied,
        "policy_id": evaluation.get("policy_id"),
        "policy_version": evaluation.get("policy_version"),
        "policy_path": evaluation.get("policy_path"),
        "finalizer_entity_id": evaluation.get("finalizer_entity_id"),
        "finalizer_role": evaluation.get("finalizer_role"),
        "evidence": evaluation.get("evidence"),
        "rules_evaluated": evaluation.get("rules_evaluated"),
        "witness_summary": {
            "witness_count": evaluation.get("witness_count"),
            "checks": evaluation.get("checks"),
            "consensus_summary": evaluation.get("consensus_summary"),
        },
    }


def finalization_policy_manifest() -> dict[str, Any]:
    policy = get_finalization_policy()
    return {
        "spec_version": policy.get("spec_version"),
        "policy_id": policy.get("policy_id"),
        "description": policy.get("description"),
        "auto_finalization_enabled": is_auto_finalization_enabled(policy),
        "default_finalizer_entity_id": finalizer_entity_id(policy),
        "finalizer_role": policy.get("finalizer_role"),
        "allowed_finalizer_entity_types": list(allowed_finalizer_entity_types(policy)),
        "verdict_routing": policy.get("verdict_routing"),
        "auto_finalize_when": policy.get("auto_finalize_when"),
        "escalate_when": policy.get("escalate_when"),
        "rules": policy.get("rules"),
        "traceability": {
            "decision_id_per_evaluation": True,
            "evidence_rows": "witnessed-by-verifier",
            "inspired_by": ["policy-bot", "maestro", "open-policy-agent"],
        },
    }


def extract_finalization_from_ledger(ledgers: list) -> dict[str, Any] | None:
    for record in reversed(ledgers):
        if record.event_type == "contribution_approved":
            payload = record.payload or {}
            block = payload.get("finalization")
            if isinstance(block, dict):
                return block
    return None


def consensus_from_contribution(contribution: ContributionEvent) -> dict[str, Any] | None:
    """Rebuild latest multi_consensus payload from stored verifier rows."""
    for row in reversed(contribution.ai_verifications or []):
        if row.model_provider == "multi_consensus":
            try:
                return json.loads(row.feedback)
            except (json.JSONDecodeError, TypeError):
                return None
    return None


def build_verdict_snapshot(contribution: ContributionEvent, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Maestro-style verdict for a contribution (inspect without mutating)."""
    policy = policy or get_finalization_policy()
    consensus = consensus_from_contribution(contribution)
    if not consensus:
        return {
            "contribution_id": contribution.id,
            "status": contribution.status.value,
            "verdict": Verdict.FAIL.value if contribution.status.value == "submitted" else Verdict.ESCALATE.value,
            "reason": "no_consensus_record",
            "policy_id": policy.get("policy_id"),
        }
    evaluation = evaluate_finalization_policy(consensus, policy)
    return {
        "contribution_id": contribution.id,
        "status": contribution.status.value,
        **evaluation,
    }


def build_proof_finalization_block(
    contribution: ContributionEvent,
    ledgers: list,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = policy or get_finalization_policy()
    approved_reviews = [r for r in contribution.human_reviews if r.approved]
    final_review = approved_reviews[-1] if approved_reviews else None
    ledger_block = extract_finalization_from_ledger(ledgers)

    mode = (ledger_block or {}).get("mode")
    if mode is None and final_review is not None:
        mode = "manual"

    return {
        "status": contribution.status.value,
        "decision_id": (ledger_block or {}).get("decision_id"),
        "verdict": (ledger_block or {}).get("verdict"),
        "finalizer_entity_id": (ledger_block or {}).get("finalizer_entity_id")
        or (final_review.reviewer_id if final_review else None),
        "mode": mode,
        "policy_id": (ledger_block or {}).get("policy_id"),
        "policy_version": (ledger_block or {}).get("policy_version"),
        "policy_path": (ledger_block or {}).get("policy_path"),
        "finalizer_role": (ledger_block or {}).get("finalizer_role"),
        "evidence": (ledger_block or {}).get("evidence"),
        "witness_summary": (ledger_block or {}).get("witness_summary"),
        "instance_policy": {
            "policy_id": policy.get("policy_id"),
            "spec_version": policy.get("spec_version"),
            "auto_finalization_enabled": is_auto_finalization_enabled(policy),
        },
    }


def try_auto_finalize_after_verify(
    db: Session,
    contribution: ContributionEvent,
    consensus: dict[str, Any],
) -> dict[str, Any] | None:
    """Apply policy-based auto-finalize when witness verdict is PASS or delegated ESCALATE."""
    if contribution.status != ContributionStatus.ai_verified:
        return None

    policy = get_finalization_policy()
    evaluation = evaluate_finalization_policy(consensus)
    verdict = evaluation["verdict"]
    pass_eligible = verdict == Verdict.PASS.value and evaluation["eligible"]
    escalate_delegate = (
        verdict == Verdict.ESCALATE.value
        and bool(policy.get("auto_finalize_on_escalate", True))
        and is_auto_finalization_enabled(policy)
    )

    if not pass_eligible and not escalate_delegate:
        return {"applied": False, **evaluation}

    if escalate_delegate and not pass_eligible:
        evaluation = {
            **evaluation,
            "mode": "witness_quorum_delegate",
            "escalated_auto_finalize": True,
            "eligible": True,
        }

    finalizer_id = evaluation["finalizer_entity_id"]
    ledger_meta = build_finalization_ledger_meta(evaluation, applied=True)
    feedback = (
        f"Auto-finalized under policy {evaluation['policy_id']} "
        f"(verdict={evaluation['verdict']}, decision_id={evaluation['decision_id']})."
    )
    rewards = approve_contribution(
        db,
        contribution,
        finalizer_id,
        feedback=feedback,
        finalization=ledger_meta,
    )
    return {
        "applied": True,
        **evaluation,
        "status": contribution.status.value,
        "rewards": rewards,
    }
