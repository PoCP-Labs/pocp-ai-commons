"""Versioned settlement policies — tagged on exchange_settled and replayable offline."""

from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from services.protocol_config import get_rewards_config

_POLICIES_PATH = Path(__file__).resolve().parent.parent / "config" / "settlement_policies.yaml"
# Alias referenced in CI-12 handoffs and Agent Studio missions (`settlement_policy.yaml`).
_POLICY_ALIAS_PATH = Path(__file__).resolve().parent.parent / "config" / "settlement_policy.yaml"
POLICY_SPEC = "pocp.settlement_policy.v0.1"


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def policy_hash(policy_body: dict[str, Any]) -> str:
    canonical = {k: v for k, v in policy_body.items() if k not in ("description",)}
    return hashlib.sha256(_stable_json(canonical).encode()).hexdigest()


@lru_cache(maxsize=1)
def _load_policies_file() -> dict[str, Any]:
    path = _POLICIES_PATH if _POLICIES_PATH.is_file() else _POLICY_ALIAS_PATH
    if not path.is_file():
        return {"policies": {}}
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {"policies": {}}


def clear_settlement_policy_cache() -> None:
    _load_policies_file.cache_clear()


def list_settlement_policies() -> list[dict[str, Any]]:
    data = _load_policies_file()
    policies = data.get("policies") or {}
    out: list[dict[str, Any]] = []
    for policy_id, body in policies.items():
        tagged = policy_tag(policy_id, body if isinstance(body, dict) else {})
        if tagged:
            out.append(tagged)
    return out


def get_settlement_policy(policy_id: str) -> dict[str, Any] | None:
    data = _load_policies_file()
    policies = data.get("policies") or {}
    body = policies.get(policy_id)
    if not isinstance(body, dict):
        return None
    return dict(body)


def policy_tag(policy_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return settlement_policy_id/version/hash block for ledger payloads."""
    doc = body or get_settlement_policy(policy_id) or {}
    if not doc:
        return {
            "settlement_policy_id": policy_id,
            "settlement_policy_version": "unknown",
            "settlement_policy": policy_id,
            "policy_hash": None,
            "spec_version": POLICY_SPEC,
        }
    pid = str(doc.get("policy_id") or policy_id)
    version = str(doc.get("version") or "1.0.0")
    digest = policy_hash(doc)
    return {
        "settlement_policy_id": pid,
        "settlement_policy_version": version,
        "settlement_policy": pid,
        "policy_hash": digest,
        "spec_version": POLICY_SPEC,
    }


def replay_bilateral_quote(
    receipt: dict[str, Any],
    *,
    policy_id: str = "compute_settlement.v1",
    db=None,
    skill_entity_id: str | None = None,
) -> dict[str, Any]:
    """Offline replay — compute expected consumer/provider amounts without mutating DB."""
    from services.compute_settlement import (
        compute_consumer_tokens,
        compute_provider_tokens,
    )
    from services.compute_metering import orchestration_split_shares

    policy = get_settlement_policy(policy_id)
    if policy is None:
        return {"valid": False, "reason": "unknown_policy", "policy_id": policy_id}

    consumer_amount = compute_consumer_tokens(receipt, db=db)
    provider_amount = compute_provider_tokens(receipt, db=db)
    consumer_id = receipt.get("initiator_entity_id")
    provider_id = receipt.get("provider_entity_id")
    if consumer_id and provider_id and consumer_id == provider_id:
        consumer_amount = 0.0

    split_shares: dict[str, float] | None = None
    skill_share = 0.0
    protocol_fee = 0.0
    if skill_entity_id and consumer_amount > 0:
        split_shares = orchestration_split_shares(consumer_amount, provider_amount)
        provider_amount = split_shares["compute_share"]
        skill_share = split_shares["skill_share"]
        protocol_fee = split_shares["protocol_fee"]

    tag = policy_tag(policy_id, policy)
    return {
        "valid": True,
        "policy_id": policy_id,
        "policy_tag": tag,
        "consumer_amount": consumer_amount,
        "provider_amount": provider_amount,
        "skill_share": skill_share,
        "protocol_fee": protocol_fee,
        "split": split_shares,
        "metering_source": policy.get("metering_source"),
        "rewards_config_version": (get_rewards_config() or {}).get("spec_version"),
    }


def replay_flat_debit_quote(
    *,
    policy_id: str = "ai_chat.v1",
    override_amount: float | None = None,
) -> dict[str, Any]:
    policy = get_settlement_policy(policy_id)
    if policy is None:
        return {"valid": False, "reason": "unknown_policy", "policy_id": policy_id}
    env_key = policy.get("flat_consumer_debit_env") or "AI_CHAT_COST_PER_MESSAGE"
    amount = override_amount
    if amount is None:
        amount = float(os.getenv(str(env_key), policy.get("default_flat_debit", 5.0)))
    tag = policy_tag(policy_id, policy)
    return {
        "valid": True,
        "policy_id": policy_id,
        "policy_tag": tag,
        "consumer_amount": amount,
        "provider_amount": amount,
        "kind": policy.get("kind"),
    }
