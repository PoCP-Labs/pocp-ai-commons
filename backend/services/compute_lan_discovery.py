"""Optional LAN compute discovery for campus deployments — Phase δ."""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from functools import lru_cache
from typing import Any

from services.compute_registry import load_compute_registry

DISCOVERY_PATH = "/api/v1/intelligence/compute/status"


def lan_discovery_enabled() -> bool:
    env = os.getenv("ENABLE_COMPUTE_LAN_DISCOVERY", "").strip().lower()
    if env in ("true", "1", "yes", "on"):
        return True
    if env in ("false", "0", "no", "off"):
        return False
    registry = load_compute_registry()
    return bool((registry.get("lan_discovery") or {}).get("enabled", False))


@lru_cache(maxsize=1)
def _static_lan_peers() -> tuple[dict[str, Any], ...]:
    registry = load_compute_registry()
    cfg = registry.get("lan_discovery") or {}
    peers: list[dict[str, Any]] = []
    for item in cfg.get("static_peers") or []:
        if not isinstance(item, dict):
            continue
        base_url = str(item.get("base_url") or "").strip().rstrip("/")
        if not base_url:
            continue
        peers.append(
            {
                "node_id": str(item.get("node_id") or base_url),
                "base_url": base_url,
                "source": "static_config",
                "label": item.get("label"),
            }
        )
    return tuple(peers)


def _probe_lan_peer(peer: dict[str, Any], timeout: float = 3.0) -> dict[str, Any]:
    base_url = peer["base_url"].rstrip("/")
    result = {**peer, "reachable": False}
    try:
        with urllib.request.urlopen(f"{base_url}{DISCOVERY_PATH}", timeout=timeout) as resp:
            status = json.loads(resp.read().decode())
        result.update(
            {
                "reachable": True,
                "compute_status": status,
                "active_adapters": status.get("active_adapters") or [],
                "node_id": status.get("node_id") or peer.get("node_id"),
            }
        )
    except urllib.error.HTTPError as exc:
        result["error"] = f"HTTP {exc.code}"
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _mdns_discover(timeout: float = 2.0) -> list[dict[str, Any]]:
    service_type = os.getenv(
        "POCP_COMPUTE_MDNS_SERVICE",
        (load_compute_registry().get("lan_discovery") or {}).get(
            "mdns_service_type", "_pocp-compute._tcp.local."
        ),
    )
    try:
        from zeroconf import ServiceBrowser, Zeroconf
    except ImportError:
        return []

    found: list[dict[str, Any]] = []

    class _Listener:
        def add_service(self, zc, type_, name):
            info = zc.get_service_info(type_, name)
            if not info:
                return
            host = socket.inet_ntoa(info.addresses[0]) if info.addresses else None
            if not host:
                return
            port = info.port or 8000
            found.append(
                {
                    "node_id": name.split(".")[0],
                    "base_url": f"http://{host}:{port}",
                    "source": "mdns",
                    "label": name,
                }
            )

        def remove_service(self, *args):
            return

        def update_service(self, *args):
            return

    zc = Zeroconf()
    try:
        ServiceBrowser(zc, service_type, _Listener())
        import time

        time.sleep(timeout)
    finally:
        zc.close()
    return found


def discover_lan_compute_peers(*, probe: bool = True) -> dict[str, Any]:
    """Advisory LAN peer list — static config + optional mDNS."""
    if not lan_discovery_enabled():
        return {
            "enabled": False,
            "peer_count": 0,
            "reachable_count": 0,
            "peers": [],
            "advisory_only": True,
        }

    peers = list(_static_lan_peers())
    if os.getenv("POCP_COMPUTE_MDNS", "").lower() in ("true", "1", "yes", "on") or (
        (load_compute_registry().get("lan_discovery") or {}).get("mdns", False)
    ):
        seen = {p["base_url"] for p in peers}
        for peer in _mdns_discover():
            if peer["base_url"] not in seen:
                peers.append(peer)
                seen.add(peer["base_url"])

    if probe:
        peers = [_probe_lan_peer(p) for p in peers]
    reachable = sum(1 for p in peers if p.get("reachable"))

    return {
        "enabled": True,
        "peer_count": len(peers),
        "reachable_count": reachable,
        "peers": peers,
        "advisory_only": True,
        "note": "LAN discovery does not auto-register providers — vouch via org mesh policy.",
    }


def clear_lan_discovery_cache() -> None:
    _static_lan_peers.cache_clear()
