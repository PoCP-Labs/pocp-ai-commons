"""Federated compute provider mirror from trusted peers — Phase δ."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from services.peer_compute import load_peer_compute_nodes, peer_compute_enabled

_CACHE: dict[str, Any] = {"fetched_at": 0.0, "providers": []}
_CACHE_TTL_SECONDS = 60


def _fetch_peer_providers(base_url: str, timeout: float = 8.0) -> list[dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/v1/compute/providers?status=active"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []

    providers = payload.get("providers") or []
    out: list[dict[str, Any]] = []
    for row in providers:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                **row,
                "federated": True,
                "source_node_base_url": base_url.rstrip("/"),
            }
        )
    return out


def list_federated_compute_providers(*, refresh: bool = False) -> dict[str, Any]:
    """Mirror org-scoped provider registry from trusted federation peers."""
    now = time.time()
    if not refresh and _CACHE["providers"] and now - float(_CACHE["fetched_at"]) < _CACHE_TTL_SECONDS:
        providers = _CACHE["providers"]
    else:
        providers: list[dict[str, Any]] = []
        if peer_compute_enabled():
            for peer in load_peer_compute_nodes():
                providers.extend(_fetch_peer_providers(peer.base_url))
        _CACHE["fetched_at"] = now
        _CACHE["providers"] = providers

    return {
        "spec_version": "0.1",
        "federation_enabled": peer_compute_enabled(),
        "provider_count": len(providers),
        "providers": providers,
        "cached_seconds": int(now - float(_CACHE["fetched_at"])),
        "advisory_only": True,
        "rule": "Trusted peer mirror — scheduling still prefers local Entity mesh.",
    }


def clear_federated_provider_cache() -> None:
    _CACHE["fetched_at"] = 0.0
    _CACHE["providers"] = []
