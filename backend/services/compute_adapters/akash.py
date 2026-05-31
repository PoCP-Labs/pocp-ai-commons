"""Akash Network compute adapter — stub + live gateway v0.1."""

from __future__ import annotations

import uuid
from typing import Any

from services.compute_adapters import akash_live
from services.compute_adapters.base import (
    AdapterJobSpec,
    AdapterJobStatus,
    AdapterPollResult,
    AdapterSubmitResult,
    ComputeAdapter,
)
from services.compute_adapters.live_config import adapter_live_enabled
from services.compute_adapters.live_http import AdapterHttpError
from services.compute_adapters.stub_state import get_stub_job, increment_stub_poll, register_stub_job


class AkashComputeAdapter(ComputeAdapter):
    slug = "akash"
    display_name = "Akash Network"
    network = "akash"
    mode = "stub"
    inspiration_slug = "akash"

    def effective_mode(self) -> str:
        return "live" if adapter_live_enabled(self.slug) else self.mode

    def submit_job(self, spec: AdapterJobSpec) -> AdapterSubmitResult:
        spec.validate()
        if adapter_live_enabled(self.slug):
            try:
                return akash_live.submit_deployment(spec)
            except AdapterHttpError as exc:
                raise ValueError(f"akash live submit failed: {exc}") from exc
        return self._submit_stub(spec)

    def poll_job(
        self,
        external_job_id: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> AdapterPollResult:
        if adapter_live_enabled(self.slug):
            if external_job_id.startswith("akash-stub-"):
                return self._poll_stub(external_job_id, context=context)
            return akash_live.poll_deployment(external_job_id, context=context)
        return self._poll_stub(external_job_id, context=context)

    def _submit_stub(self, spec: AdapterJobSpec) -> AdapterSubmitResult:
        external_job_id = f"akash-stub-{uuid.uuid4().hex[:12]}"
        register_stub_job(
            external_job_id,
            spec_snapshot={
                "capability": spec.capability,
                "provider_entity_id": spec.provider_entity_id,
                "contribution_id": spec.contribution_id,
                "task_id": spec.task_id,
            },
            network=self.network,
        )
        return AdapterSubmitResult(
            external_job_id=external_job_id,
            status=AdapterJobStatus.queued,
            metadata={"deployment_mode": "stub", "lease_required": False},
        )

    def _poll_stub(
        self,
        external_job_id: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> AdapterPollResult:
        if get_stub_job(external_job_id) is None:
            return AdapterPollResult(
                status=AdapterJobStatus.failed,
                error=f"unknown Akash job: {external_job_id}",
            )
        polls = increment_stub_poll(external_job_id)
        if polls < 2:
            return AdapterPollResult(
                status=AdapterJobStatus.running,
                metadata={"poll_count": polls, "deployment_mode": "stub"},
            )
        gpu_seconds = 1.0
        if context and context.get("gpu_seconds") is not None:
            gpu_seconds = float(context["gpu_seconds"])
        return AdapterPollResult(
            status=AdapterJobStatus.succeeded,
            output_material="[PoCP Akash stub] Inference complete on leased deployment.",
            resource_units={
                "gpu_seconds": gpu_seconds,
                "network": "akash",
                "currency_note": "AKT settlement external to PoCP ledger",
            },
            metadata={"poll_count": polls, "deployment_status": "active", "deployment_mode": "stub"},
        )

    def map_failure(self, error: str) -> dict[str, Any]:
        mapped = super().map_failure(error)
        lowered = (error or "").lower()
        if "not configured" in lowered or "timeout" in lowered or "network" in lowered:
            mapped["code"] = "adapter_unavailable"
        elif "unknown" in lowered or "not found" in lowered:
            mapped["code"] = "job_not_found"
        return mapped
