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
    return merged
