"""Shared HTTP helpers for live compute adapter wire clients."""

from __future__ import annotations

from typing import Any

import httpx

from services.compute_adapters.live_config import adapter_api_token, adapter_http_timeout


class AdapterHttpError(Exception):
    def __init__(self, message: str, *, code: str = "adapter_unavailable", status_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def request_json(
    method: str,
    url: str,
    *,
    slug: str,
    json_body: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    headers: dict[str, str] = {"Accept": "application/json"}
    token = adapter_api_token(slug)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with httpx.Client(timeout=timeout or adapter_http_timeout()) as client:
            response = client.request(method.upper(), url, headers=headers, json=json_body)
    except httpx.TimeoutException as exc:
        raise AdapterHttpError("adapter network timeout", code="adapter_unavailable") from exc
    except httpx.HTTPError as exc:
        raise AdapterHttpError("adapter network error", code="adapter_unavailable") from exc

    if response.status_code == 404:
        raise AdapterHttpError("job not found", code="job_not_found", status_code=404)
    if response.status_code >= 400:
        detail = response.text[:200] if response.text else f"HTTP {response.status_code}"
        raise AdapterHttpError(detail, code="adapter_unavailable", status_code=response.status_code)

    try:
        payload = response.json()
    except ValueError as exc:
        raise AdapterHttpError("invalid JSON from adapter gateway", code="adapter_unavailable") from exc
    if not isinstance(payload, dict):
        raise AdapterHttpError("adapter gateway returned non-object JSON", code="adapter_unavailable")
    return payload
