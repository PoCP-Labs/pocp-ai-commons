"""CP / AIC / CC metering audit — CI-12 protocol economy gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from services.token_measurement.base import SUPPORTED_UNITS
from services.token_measurement.no_token_guard import lex_compliance_report

_AUDIT_SPEC = "pocp.protocol_economy_audit.v0.1"
_REPO_ROOT = Path(__file__).resolve().parents[3]

# Canonical unit labels in protocol docs ↔ runtime wallet / CIP fields.
_UNIT_FIELD_MAP: dict[str, dict[str, str]] = {
    "CP": {"wallet_field": "cp_balance", "credit_type": "cp", "visibility": "internal"},
    "AIC": {"wallet_field": "ai_credits", "credit_type": "ai_credits", "visibility": "internal"},
    "CC": {
        "wallet_field": "compute_credit_balance",
        "credit_type": None,
        "visibility": "internal_cip",
    },
    "PT": {
        "wallet_field": "pocp_token_balance_internal",
        "credit_type": None,
        "visibility": "internal_only",
    },
}


def audit_metering_units() -> dict[str, Any]:
    """Verify supported units, wallet mapping, and compute metering wallet field."""
    from services.compute_metering import unified_token_enabled, wallet_field

    issues: list[str] = []
    wallet_map = wallet_field()
    if wallet_map != _UNIT_FIELD_MAP["AIC"]["wallet_field"]:
        issues.append(f"compute_metering.wallet_field={wallet_map!r} != AIC wallet column")

    units_doc = _REPO_ROOT / "docs" / "protocol" / "TOKEN-MEASUREMENT-SCHEMA-v0.3.md"
    doc_text = units_doc.read_text(encoding="utf-8") if units_doc.is_file() else ""
    for unit in SUPPORTED_UNITS:
        if unit not in doc_text:
            issues.append(f"TOKEN-MEASUREMENT-SCHEMA missing unit {unit}")

    return {
        "valid": not issues,
        "spec_version": _AUDIT_SPEC,
        "supported_units": sorted(SUPPORTED_UNITS),
        "unit_field_map": _UNIT_FIELD_MAP,
        "unified_token_metering": unified_token_enabled(),
        "wallet_field_for_metering": wallet_map,
        "issues": issues,
    }


def audit_settlement_policy_config() -> dict[str, Any]:
    """Validate settlement_policies.yaml structure, hashes, and metering references."""
    from services.settlement_policy import (
        POLICY_SPEC,
        get_settlement_policy,
        list_settlement_policies,
        policy_tag,
    )

    issues: list[str] = []
    policies = list_settlement_policies()
    if not policies:
        issues.append("no settlement policies loaded")

    accounting = {}
    try:
        from services.settlement_policy import _load_policies_file

        accounting = _load_policies_file().get("accounting_units") or {}
    except Exception as exc:  # pragma: no cover - defensive
        issues.append(f"accounting_units load failed: {exc}")

    for unit in ("CP", "AIC", "CC"):
        meta = accounting.get(unit)
        if not isinstance(meta, dict):
            issues.append(f"accounting_units.{unit} missing")
        elif meta.get("visibility") != "internal":
            issues.append(f"accounting_units.{unit} must be internal")

    pt_meta = accounting.get("PT")
    if not isinstance(pt_meta, dict):
        issues.append("accounting_units.PT missing")
    elif pt_meta.get("visibility") != "internal_only":
        issues.append("accounting_units.PT must be internal_only")

    for tagged in policies:
        pid = tagged.get("settlement_policy_id")
        if not tagged.get("policy_hash"):
            issues.append(f"policy {pid} missing policy_hash")
        body = get_settlement_policy(str(pid))
        if body is None:
            issues.append(f"policy {pid} body missing")
            continue
        kind = body.get("kind")
        if kind == "bilateral_metered" and not body.get("metering_source"):
            issues.append(f"policy {pid} bilateral_metered missing metering_source")
        tag = policy_tag(str(pid), body)
        if tag.get("spec_version") != POLICY_SPEC:
            issues.append(f"policy {pid} spec_version mismatch")

    return {
        "valid": not issues,
        "spec_version": _AUDIT_SPEC,
        "policy_count": len(policies),
        "policies": [p.get("settlement_policy_id") for p in policies],
        "accounting_units": accounting,
        "issues": issues,
    }


def audit_protocol_economy() -> dict[str, Any]:
    """Combined CI-12 gate: metering units + settlement policies + Lex NO-TOKEN-FIRST."""
    metering = audit_metering_units()
    policies = audit_settlement_policy_config()
    lex = lex_compliance_report()
    valid = metering["valid"] and policies["valid"] and lex["valid"]
    return {
        "valid": valid,
        "spec_version": _AUDIT_SPEC,
        "metering": metering,
        "settlement_policies": policies,
        "no_token_first": lex,
    }
