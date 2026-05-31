"""Akash live wire client — PoCP gateway API v0.1.

Gateway contract (operator-hosted bridge to Akash deployments):
  POST {POCP_AKASH_API_URL}/v1/deployments
  GET  {POCP_AKASH_API_URL}/v1/deployments/{deployment_id}

See docs/COMPUTE-ADAPTER-LIVE-WIRE.md
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from services.compute_adapters.base import (
    AdapterJobSpec,
    AdapterJobStatus,
    AdapterPollResult,
    AdapterSubmitResult,
)
from services.compute_adapters.live_config import adapter_api_url
from services.compute_adapters.live_http import AdapterHttpError, request_json

_AKASH_SLUG = "akash"

_RUNNING = frozenset({"pending", "activating", "deploying", "running", "queued"})
_SUCCEEDED = frozenset({"active", "succeeded", "complete", "completed"})
_FAILED = frozenset({"failed", "error", "closed", "cancelled"})


def _base_url() -> str:
    base = adapter_api_url(_AKASH_SLUG)
    if not base:
        raise AdapterHttpError("POCP_AKASH_API_URL not configured", code="adapter_unavailable")
    return base.rstrip("/") + "/"


def _map_status(raw: str | None) -> AdapterJobStatus:
    normalized = (raw or "").strip().lower()
    if normalized in _SUCCEEDED:
        return AdapterJobStatus.succeeded
    if normalized in _FAILED:
        return AdapterJobStatus.failed
    if normalized in _RUNNING:
        return AdapterJobStatus.running
    return AdapterJobStatus.queued


def submit_deployment(spec: AdapterJobSpec) -> AdapterSubmitResult:
    url = urljoin(_base_url(), "v1/deployments")
    body = {
        "capability": spec.capability,
        "contribution_id": spec.contribution_id,
        "task_id": spec.task_id,
        "trace_id": spec.trace_id,
        "requester_entity_id": spec.requester_entity_id,
        "provider_entity_id": spec.provider_entity_id,
        "constraints": spec.constraints,
    }
    try:
        payload = request_json("POST", url, slug=_AKASH_SLUG, json_body=body)
    except AdapterHttpError:
        raise

    deployment_id = str(
        payload.get("deployment_id") or payload.get("external_job_id") or payload.get("job_id") or ""
    ).strip()
    if not deployment_id:
        raise AdapterHttpError("gateway missing deployment_id", code="adapter_unavailable")

    return AdapterSubmitResult(
        external_job_id=deployment_id,
        status=_map_status(str(payload.get("status") or "pending")),
        metadata={
            "deployment_mode": "live",
            "gateway": "pocp.akash_gateway.v0.1",
            "lease_required": bool(payload.get("lease_required", True)),
        },
    )


def poll_deployment(
    external_job_id: str,
    *,
    context: dict[str, Any] | None = None,
) -> AdapterPollResult:
    url = urljoin(_base_url(), f"v1/deployments/{external_job_id}")
    try:
        payload = request_json("GET", url, slug=_AKASH_SLUG)
    except AdapterHttpError as exc:
        if exc.code == "job_not_found":
            return AdapterPollResult(status=AdapterJobStatus.failed, error="unknown Akash deployment")
        return AdapterPollResult(status=AdapterJobStatus.failed, error=str(exc))

    status = _map_status(str(payload.get("status")))
    if status == AdapterJobStatus.failed:
        return AdapterPollResult(
            status=AdapterJobStatus.failed,
            error=str(payload.get("error") or payload.get("message") or "deployment failed"),
            metadata={"deployment_status": payload.get("status")},
        )
    if status != AdapterJobStatus.succeeded:
        return AdapterPollResult(
            status=status,
            metadata={
                "deployment_status": payload.get("status"),
                "poll_count": (context or {}).get("poll_count"),
            },
        )

    gpu_seconds = payload.get("gpu_seconds")
    if gpu_seconds is None and context and context.get("gpu_seconds") is not None:
        gpu_seconds = float(context["gpu_seconds"])
    if gpu_seconds is None:
        gpu_seconds = 1.0

    resource_units: dict[str, Any] = {
        "gpu_seconds": float(gpu_seconds),
        "network": "akash",
        "currency_note": "AKT settlement external to PoCP ledger",
    }
    settlement_ref = payload.get("external_settlement_ref") or payload.get("akt_tx")
    integrity: dict[str, Any] = {}
    if settlement_ref:
        integrity["external_settlement_ref"] = str(settlement_ref)

    output = payload.get("output_preview") or payload.get("output_material")
    if not output:
        output = "[PoCP Akash live] Inference complete on leased deployment."

    return AdapterPollResult(
        status=AdapterJobStatus.succeeded,
        output_material=str(output),
        resource_units=resource_units,
        metadata={
            "deployment_mode": "live",
            "deployment_status": payload.get("status"),
            "gateway": "pocp.akash_gateway.v0.1",
            **({"integrity": integrity} if integrity else {}),
        },
    )
