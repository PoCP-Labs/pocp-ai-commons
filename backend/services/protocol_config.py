"""Load versioned protocol parameters from YAML (not hardcoded in services)."""

from functools import lru_cache
from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "pocp_rewards.yaml"

_DEFAULTS = {
    "spec_version": "0.1",
    "registration": {"ai_credits": 100},
    "contribution_defaults": {
        "human": {"cp_base": 20, "ai_credits_base": 80},
        "skill": {"reputation_base": 5},
        "agent": {"reputation_base": 3},
    },
}


@lru_cache(maxsize=1)
def get_rewards_config() -> dict:
    if not _CONFIG_PATH.exists():
        return _DEFAULTS
    with _CONFIG_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    merged = dict(_DEFAULTS)
    merged.update({k: v for k, v in data.items() if k != "contribution_defaults"})
    if "contribution_defaults" in data:
        defaults = dict(_DEFAULTS["contribution_defaults"])
        for role, values in data["contribution_defaults"].items():
            defaults[role] = {**defaults.get(role, {}), **values}
        merged["contribution_defaults"] = defaults
    return merged
