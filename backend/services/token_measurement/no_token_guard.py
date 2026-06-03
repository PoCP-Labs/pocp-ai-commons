"""Lex-0 NO-TOKEN-FIRST compliance guard for protocol economy surfaces."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

NO_TOKEN_FIRST_SPEC = "pocp.no_token_first_guard.v0.1"

_REPO_ROOT = Path(__file__).resolve().parents[3]

# Blocked public-economics phrases (case-insensitive). Context-aware review still required.
_FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("airdrop", re.compile(r"\bairdrop(s)?\b", re.I)),
    ("dex_listing", re.compile(r"\b(dex|decentralized exchange)\b", re.I)),
    ("staking_yield", re.compile(r"\b(staking|stake-to-earn)\b", re.I)),
    ("guaranteed_return", re.compile(r"\bguaranteed return(s)?\b", re.I)),
    ("investment_product", re.compile(r"\b(invest(ment|or)|financial return|ROI)\b", re.I)),
    ("tradable_token_marketing", re.compile(r"\btradable (protocol )?token\b", re.I)),
    ("token_launch_marketing", re.compile(r"\btoken (launch|sale|ICO|IDO)\b", re.I)),
)

# Paths Prism-0 owns for CI-12 economy audit (internal accounting docs only).
_DEFAULT_SCAN_PATHS = (
    _REPO_ROOT / "docs" / "protocol" / "TOKEN-MEASUREMENT-SCHEMA-v0.3.md",
    _REPO_ROOT / "docs" / "protocol" / "SETTLEMENT-SPEC.md",
    _REPO_ROOT / "docs" / "protocol" / "SETTLEMENT-SCHEMA-v0.3.md",
    _REPO_ROOT / "docs" / "protocol" / "PROTOCOL-ECONOMY-SPEC.md",
    _REPO_ROOT / "backend" / "config" / "settlement_policies.yaml",
)

# Policy YAML keys that would violate NO-TOKEN-FIRST if present.
_FORBIDDEN_POLICY_KEYS = frozenset(
    {
        "public_tradable",
        "dex_listing",
        "airdrop_eligible",
        "staking_rewards",
        "token_sale",
        "investment_return",
    }
)


def _is_negated_context(line: str, match: re.Match[str]) -> bool:
    """Allow explicit anti-token-first wording (e.g. 'not a tradable token')."""
    window = line.lower()
    negators = (
        "not a tradable",
        "not tradable",
        "no tradable",
        "not a public",
        "no public token",
        "internal-only",
        "internal only",
        "internal account",
        "does not mean",
    )
    return any(n in window for n in negators)


def _scan_text(path: Path, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for label, pattern in _FORBIDDEN_PATTERNS:
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            line = text.splitlines()[line_no - 1] if line_no else ""
            if _is_negated_context(line, match):
                continue
            findings.append(
                {
                    "path": str(path.relative_to(_REPO_ROOT)),
                    "line": line_no,
                    "rule": label,
                    "excerpt": text[max(0, match.start() - 20) : match.end() + 20].strip(),
                }
            )
    return findings


def _check_policy_keys(policy_body: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for key in policy_body:
        if key in _FORBIDDEN_POLICY_KEYS:
            findings.append(
                {
                    "path": "settlement_policies.yaml",
                    "line": None,
                    "rule": f"forbidden_policy_key:{key}",
                    "excerpt": key,
                }
            )
    return findings


def check_no_token_first_compliance(
    paths: list[Path] | None = None,
    *,
    policy_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return Lex-style PASS/BLOCK report for protocol economy copy and policy YAML."""
    scan_paths = paths or list(_DEFAULT_SCAN_PATHS)
    findings: list[dict[str, Any]] = []

    for path in scan_paths:
        if not path.is_file():
            findings.append({"path": str(path), "rule": "missing_file", "line": None, "excerpt": None})
            continue
        findings.extend(_scan_text(path, path.read_text(encoding="utf-8")))

    if policy_body:
        findings.extend(_check_policy_keys(policy_body))

    verdict = "PASS" if not findings else "BLOCK"
    return {
        "valid": verdict == "PASS",
        "verdict": verdict,
        "spec_version": NO_TOKEN_FIRST_SPEC,
        "findings": findings,
        "scanned_paths": [str(p.relative_to(_REPO_ROOT)) for p in scan_paths if p.is_file()],
    }


def lex_compliance_report() -> dict[str, Any]:
    """Convenience wrapper for Agent Studio / CI gates."""
    from services.settlement_policy import _load_policies_file

    report = check_no_token_first_compliance()
    policy_data = _load_policies_file()
    guard = policy_data.get("no_public_token_guard") or {}
    if guard.get("enabled") is not True:
        report["valid"] = False
        report["verdict"] = "BLOCK"
        report["findings"].append(
            {
                "path": "backend/config/settlement_policies.yaml",
                "line": None,
                "rule": "no_public_token_guard_disabled",
                "excerpt": "no_public_token_guard.enabled must be true",
            }
        )
    for policy_id, body in (policy_data.get("policies") or {}).items():
        if isinstance(body, dict):
            for finding in _check_policy_keys(body):
                finding["policy_id"] = policy_id
                report["findings"].append(finding)
    if report["findings"]:
        report["valid"] = False
        report["verdict"] = "BLOCK"
    return report
