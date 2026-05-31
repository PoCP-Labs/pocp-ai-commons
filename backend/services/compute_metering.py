"""Token metering for compute & intelligence — v0.2."""

from __future__ import annotations

import os
from typing import Any

from services.protocol_config import get_rewards_config


def _metering_cfg() -> dict[str, Any]:
    return get_rewards_config().get("compute_metering") or {}


def unified_token_enabled() -> bool:
    raw = os.getenv("POCP_UNIFIED_TOKEN")
    if raw is not None:
        return raw.lower() in ("1", "true", "yes")
    return bool(_metering_cfg().get("unified_token", True))


def token_unit() -> str:
    return str(_metering_cfg().get("token_unit") or "pocp_token")


def wallet_field() -> str:
    """DB wallet column — 1 PoCP Token = 1 ai_credits (same unit)."""
    return "ai_credits"


def metering_mode() -> str:
    return (
        os.getenv("POCP_COMPUTE_METERING_MODE")
        or _metering_cfg().get("mode")
        or "receipt"
    ).lower()


def _model_rates(model: str | None) -> dict[str, float]:
    cfg = _metering_cfg()
    models = cfg.get("models") or {}
    key = (model or "default").strip() or "default"
    base = dict(models.get("default") or {})
    if key != "default" and key in models:
        base.update(models[key])
    return {
        "consumer_per_1k_prompt": float(base.get("consumer_per_1k_prompt", 0.5)),
        "consumer_per_1k_completion": float(base.get("consumer_per_1k_completion", 1.0)),
        "provider_per_1k_total": float(base.get("provider_per_1k_total", 0.3)),
        "base_consumer": float(base.get("base_consumer", 0.0)),
        "base_provider": float(base.get("base_provider", 0.0)),
    }


def _chars_to_tokens(text: str) -> int:
    return max(1, (len(text or "") + 3) // 4)


def estimate_token_usage(
    *,
    prompt: str,
    output: str,
    system: str = "",
    estimator: str | None = None,
) -> dict[str, Any]:
    est = estimator or _metering_cfg().get("fallback_estimator") or "chars/4"
    prompt_tokens = _chars_to_tokens(f"{system}\n{prompt}".strip())
    completion_tokens = _chars_to_tokens(output)
    total = prompt_tokens + completion_tokens
    return {
        "metering_mode": "token",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total,
        "intel_equivalent_tokens": 0,
        "estimated": True,
        "estimator": est,
    }


def usage_from_adapter(
    adapter_usage: dict[str, Any] | None,
    *,
    prompt: str,
    output: str,
    system: str = "",
) -> dict[str, Any]:
    if adapter_usage:
        prompt_tokens = int(adapter_usage.get("prompt_tokens") or 0)
        completion_tokens = int(adapter_usage.get("completion_tokens") or 0)
        total = int(adapter_usage.get("total_tokens") or prompt_tokens + completion_tokens)
        return {
            "metering_mode": "token",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total,
            "intel_equivalent_tokens": 0,
            "estimated": False,
            "estimator": None,
        }
    return estimate_token_usage(prompt=prompt, output=output, system=system)


def intel_usage_for_service(service: str) -> dict[str, Any]:
    cfg = _metering_cfg()
    intel = (cfg.get("intel") or {}).get(service) or {}
    eq = int(intel.get("intel_equivalent_tokens") or 1000)
    return {
        "metering_mode": "intel",
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "intel_equivalent_tokens": eq,
        "intel_units": 1,
        "estimated": False,
        "estimator": None,
        "service": service,
    }


def _round_tokens(value: float) -> float:
    return round(max(value, 0.0), 4)


def consumer_tokens_for_usage(
    usage: dict[str, Any] | None,
    *,
    model: str | None,
    capability: str = "llm_inference",
    execution_mode: str = "live_inference",
) -> float:
    """PoCP Tokens debited from consumer Wallet (unified metering + settlement)."""
    cfg = _metering_cfg()
    mode = usage.get("metering_mode") if usage else metering_mode()

    if execution_mode == "cache_hit":
        mult = float((cfg.get("artifact") or {}).get("cache_hit_consumer_multiplier") or 0.1)
        live = consumer_tokens_for_usage(
            usage,
            model=model,
            capability=capability,
            execution_mode="live_inference",
        )
        return _round_tokens(max(live * mult, float(cfg.get("min_consumer_tokens") or cfg.get("min_consumer_credits") or 0.1)))

    if mode == "intel" or (usage and usage.get("service")):
        service = (usage or {}).get("service") or capability
        intel = (cfg.get("intel") or {}).get(service) or {}
        amount = intel.get("consumer_tokens", intel.get("consumer_credits", 5.0))
        return _round_tokens(float(amount))

    if metering_mode() == "receipt" and not usage:
        return float(os.getenv("SKILL_EXECUTE_COST", "5"))

    if not usage:
        usage = estimate_token_usage(prompt="", output="")

    rates = _model_rates(model)
    prompt = int(usage.get("prompt_tokens") or 0)
    completion = int(usage.get("completion_tokens") or 0)
    intel_eq = int(usage.get("intel_equivalent_tokens") or 0)
    tokens = (
        rates["base_consumer"]
        + (prompt / 1000.0) * rates["consumer_per_1k_prompt"]
        + (completion / 1000.0) * rates["consumer_per_1k_completion"]
        + (intel_eq / 1000.0) * rates["consumer_per_1k_prompt"]
    )
    minimum = float(cfg.get("min_consumer_tokens") or cfg.get("min_consumer_credits") or 0.1)
    return _round_tokens(max(tokens, minimum))


def provider_tokens_for_usage(
    usage: dict[str, Any] | None,
    *,
    model: str | None,
    capability: str = "llm_inference",
    execution_mode: str = "live_inference",
) -> float:
    """PoCP Tokens credited to provider Wallet (unified metering + settlement)."""
    cfg = _metering_cfg()
    legacy = get_rewards_config().get("compute_provider") or {}

    if execution_mode == "cache_hit":
        mult = float((cfg.get("artifact") or {}).get("cache_hit_provider_multiplier") or 0.05)
        live = provider_tokens_for_usage(
            usage,
            model=model,
            capability=capability,
            execution_mode="live_inference",
        )
        return _round_tokens(live * mult)

    mode = usage.get("metering_mode") if usage else metering_mode()

    if mode == "intel" or (usage and usage.get("service")):
        service = (usage or {}).get("service") or capability
        intel = (cfg.get("intel") or {}).get(service) or {}
        amount = intel.get("provider_tokens", intel.get("provider_credits", 3.0))
        return _round_tokens(float(amount))

    if metering_mode() == "receipt" and not usage:
        return float(
            legacy.get(
                "ai_credits_per_receipt",
                os.getenv("POCP_COMPUTE_PROVIDER_CREDITS", "1"),
            )
        )

    if not usage:
        usage = estimate_token_usage(prompt="", output="")

    rates = _model_rates(model)
    total = int(usage.get("total_tokens") or 0)
    tokens = rates["base_provider"] + (total / 1000.0) * rates["provider_per_1k_total"]

    if usage.get("estimated"):
        discount = float(cfg.get("estimated_provider_discount") or 0.5)
        tokens *= discount

    minimum = float(cfg.get("min_provider_tokens") or cfg.get("min_provider_credits") or 0.05)
    return _round_tokens(max(tokens, minimum))


def burn_tokens_from_receipt(receipt: dict[str, Any] | None) -> float:
    if not receipt:
        return float(os.getenv("SKILL_EXECUTE_COST", "5"))
    extra = receipt.get("extra") or {}
    usage = extra.get("usage")
    execution_mode = extra.get("execution_mode") or "live_inference"
    return consumer_tokens_for_usage(
        usage,
        model=receipt.get("model"),
        capability=str(receipt.get("capability") or "llm_inference"),
        execution_mode=execution_mode,
    )


def settlement_block(
    usage: dict[str, Any] | None,
    *,
    pocp_tokens_consumer: float,
    pocp_tokens_provider: float | None = None,
) -> dict[str, Any]:
    """Unified settlement payload for Receipt / Ledger."""
    u = usage or {}
    return {
        "unified_token": unified_token_enabled(),
        "token_unit": token_unit(),
        "llm_prompt_tokens": int(u.get("prompt_tokens") or 0),
        "llm_completion_tokens": int(u.get("completion_tokens") or 0),
        "llm_total_tokens": int(u.get("total_tokens") or 0),
        "intel_equivalent_tokens": int(u.get("intel_equivalent_tokens") or 0),
        "pocp_tokens_consumer": pocp_tokens_consumer,
        "pocp_tokens_provider": pocp_tokens_provider,
    }


# Backward-compatible aliases (1 PoCP Token == 1 ai_credits in Wallet)
consumer_credits_for_usage = consumer_tokens_for_usage
provider_credits_for_usage = provider_tokens_for_usage
burn_credits_from_receipt = burn_tokens_from_receipt
_round_credits = _round_tokens
