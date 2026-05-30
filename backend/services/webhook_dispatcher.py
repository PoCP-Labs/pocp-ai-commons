"""Optional outbound webhooks for review workflow events."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import httpx
import yaml

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "webhooks.yaml"


def _load_webhooks() -> list[dict[str, Any]]:
    if not CONFIG_PATH.exists():
        return []
    try:
        data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    hooks = data.get("webhooks") or []
    return [item for item in hooks if isinstance(item, dict) and item.get("enabled", True)]


def dispatch_review_event(event_type: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Fire configured webhooks; failures are logged but never block the main flow."""
    if os.getenv("POCP_DISABLE_WEBHOOKS", "false").lower() == "true":
        return []

    results: list[dict[str, Any]] = []
    for hook in _load_webhooks():
        url = str(hook.get("url") or "").strip()
        if not url:
            continue
        events = hook.get("events") or ["contribution.approved", "contribution.rejected", "contribution.request_changes"]
        if event_type not in events:
            continue

        headers = {"Content-Type": "application/json"}
        secret = hook.get("secret") or os.getenv(hook.get("secret_env") or "")
        if secret:
            headers["X-PoCP-Webhook-Secret"] = secret

        body = {"event": event_type, "payload": payload}
        try:
            with httpx.Client(timeout=float(hook.get("timeout_seconds") or 5)) as client:
                response = client.post(url, headers=headers, json=body)
            results.append({"url": url, "status_code": response.status_code, "ok": response.status_code < 400})
        except Exception as exc:
            logger.warning("Webhook dispatch failed for %s: %s", url, exc)
            results.append({"url": url, "ok": False, "error": str(exc)})
    return results
