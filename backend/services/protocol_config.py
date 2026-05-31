"""Load versioned protocol parameters from YAML (not hardcoded in services)."""

from functools import lru_cache
from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "pocp_rewards.yaml"

_DEFAULTS = {
    "spec_version": "0.1",
    "registration": {"ai_credits": 100},
    "rights": {
        "bc": {
            "version": "bc_v0_1",
            "spendable": True,
            "transferable": False,
            "description": "AI Credits spendable on protocol AI services",
        },
        "cp": {
            "version": "cp_v0_1",
            "spendable": False,
            "transferable": False,
            "description": "Non-spendable contribution proof",
        },
    },
    "contribution_defaults": {
        "human": {"cp_base": 20, "ai_credits_base": 80, "reputation_base": 10},
        "skill": {"reputation_base": 5},
        "agent": {"reputation_base": 3},
    },
    "compute_provider": {
        "reputation_per_receipt": 0.5,
        "reputation_scheduler_weight": 0.15,
        "ai_credits_per_receipt": 1.0,
    },
    "compute_metering": {
        "unified_token": True,
        "token_unit": "pocp_token",
        "mode": "receipt",
        "min_consumer_credits": 0.1,
        "min_provider_credits": 0.05,
        "models": {"default": {"consumer_per_1k_prompt": 0.5, "consumer_per_1k_completion": 1.0, "provider_per_1k_total": 0.3}},
        "intel": {"witness": {"provider_credits": 3.0, "consumer_credits": 5.0}},
        "artifact": {"cache_hit_consumer_multiplier": 0.1, "cache_hit_provider_multiplier": 0.05},
    },
    "compute_surplus": {
        "enabled": True,
        "idle_window_hours": 1,
        "idle_job_threshold": 0,
        "pool_deposit_pct": 0.20,
        "deficit_burst_limit": 500,
        "auto_balance_enabled": False,
        "auto_balance_interval_minutes": 60,
        "auto_recycle_on_surplus": True,
    },
    "federation": {"default_trust_weight": 0.5},
}


@lru_cache(maxsize=1)
def get_rewards_config() -> dict:
    if not _CONFIG_PATH.exists():
        return _DEFAULTS
    with _CONFIG_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    merged = dict(_DEFAULTS)
    merged.update(
        {k: v for k, v in data.items() if k not in ("contribution_defaults", "federation", "rights")}
    )
    if "federation" in data:
        merged["federation"] = {**_DEFAULTS.get("federation", {}), **data["federation"]}
    if "rights" in data:
        rights = dict(_DEFAULTS["rights"])
        for kind, values in data["rights"].items():
            rights[kind] = {**rights.get(kind, {}), **values}
        merged["rights"] = rights
    if "contribution_defaults" in data:
        defaults = dict(_DEFAULTS["contribution_defaults"])
        for role, values in data["contribution_defaults"].items():
            defaults[role] = {**defaults.get(role, {}), **values}
        merged["contribution_defaults"] = defaults
    if "compute_provider" in data:
        merged["compute_provider"] = {**_DEFAULTS.get("compute_provider", {}), **data["compute_provider"]}
    if "compute_metering" in data:
        merged["compute_metering"] = {**_DEFAULTS.get("compute_metering", {}), **data["compute_metering"]}
    if "compute_surplus" in data:
        merged["compute_surplus"] = {**_DEFAULTS.get("compute_surplus", {}), **data["compute_surplus"]}
    return merged
