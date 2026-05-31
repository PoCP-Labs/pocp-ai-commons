"""Resolve live vs stub mode for external compute adapters from environment."""

from __future__ import annotations

import os

ADAPTER_ENV_KEYS: dict[str, str] = {
    "akash": "POCP_AKASH_API_URL",
    "render-network": "POCP_RENDER_API_URL",
    "io-net": "POCP_IONET_API_URL",
    "gensyn": "POCP_GENSYN_API_URL",
}

ADAPTER_AUTH_ENV_KEYS: dict[str, str] = {
    "akash": "POCP_AKASH_API_TOKEN",
    "render-network": "POCP_RENDER_API_TOKEN",
    "io-net": "POCP_IONET_API_TOKEN",
    "gensyn": "POCP_GENSYN_API_TOKEN",
}

# Phase 1 live wire clients implemented in-repo
LIVE_WIRE_ADAPTERS = frozenset({"akash"})


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def adapter_http_timeout() -> float:
    raw = os.getenv("POCP_ADAPTER_HTTP_TIMEOUT", "120").strip()
    try:
        return max(float(raw), 5.0)
    except ValueError:
        return 120.0


def adapter_api_url(slug: str) -> str | None:
    key = ADAPTER_ENV_KEYS.get(slug.strip().lower())
    if not key:
        return None
    value = os.getenv(key, "").strip()
    return value or None


def adapter_api_token(slug: str) -> str | None:
    key = ADAPTER_AUTH_ENV_KEYS.get(slug.strip().lower())
    if not key:
        return None
    value = os.getenv(key, "").strip()
    return value or None


def adapter_live_configured(slug: str) -> bool:
    return adapter_api_url(slug) is not None


def adapter_live_enabled(slug: str) -> bool:
    normalized = slug.strip().lower()
    if normalized not in LIVE_WIRE_ADAPTERS:
        return False
    if not adapter_live_configured(normalized):
        return False
    per_adapter = ADAPTER_ENV_KEYS.get(normalized, "").replace("_API_URL", "_LIVE_ENABLED")
    if per_adapter and _env_truthy(per_adapter):
        return True
    return _env_truthy("POCP_ADAPTER_LIVE_ENABLED")


def effective_adapter_mode(slug: str, *, default: str = "stub") -> str:
    return "live" if adapter_live_enabled(slug) else default


def adapter_runtime_status(slug: str, *, default: str = "stub") -> dict[str, str | bool]:
    configured = adapter_live_configured(slug)
    active = adapter_live_enabled(slug)
    mode = effective_adapter_mode(slug, default=default)

    if active:
        note = "Live wire active — jobs call external gateway."
    elif configured:
        note = "POCP_*_API_URL set — enable POCP_ADAPTER_LIVE_ENABLED=true to activate."
    else:
        note = "Stub adapter — set POCP_*_API_URL to prepare live wire."

    return {
        "mode": mode,
        "live_configured": configured,
        "live_wire_active": active,
        "note": note,
    }
