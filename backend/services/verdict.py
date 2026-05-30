"""Maestro-inspired verdict routing — PASS / ESCALATE / FAIL / BLOCK."""

from __future__ import annotations

from enum import Enum
from typing import Any


class Verdict(str, Enum):
    """Completion gate for a contribution after verification."""

    PASS = "PASS"  # auto-finalize allowed when policy checks pass
    ESCALATE = "ESCALATE"  # ai_verified — queue for any traceable finalizer
    FAIL = "FAIL"  # verification did not pass
    BLOCK = "BLOCK"  # policy hold (abuse, missing evidence, etc.)


def compute_verdict(
    *,
    consensus: dict[str, Any],
    checks: dict[str, bool],
    auto_finalize_eligible: bool,
    policy: dict[str, Any],
) -> Verdict:
    """Route like maestro: witnessed evidence → verdict → gate."""
    routing = policy.get("verdict_routing") or {}
    if not consensus.get("passed", False):
        return Verdict(routing.get("fail", Verdict.FAIL.value))

    escalate_rules = (policy.get("escalate_when") or {}).get("any_of") or []
    for rule_name in escalate_rules:
        if checks.get(rule_name):
            return Verdict(routing.get("escalate", Verdict.ESCALATE.value))

    if auto_finalize_eligible and checks.get("auto_finalization_enabled"):
        return Verdict(routing.get("pass", Verdict.PASS.value))

    return Verdict(routing.get("escalate", Verdict.ESCALATE.value))
