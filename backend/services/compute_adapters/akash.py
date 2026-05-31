"""Akash Network compute adapter — stub v0.1."""

from __future__ import annotations

import uuid
from typing import Any

from services.compute_adapters.base import (
    AdapterJobSpec,
    AdapterJobStatus,
    AdapterPollResult,
    AdapterSubmitResult,
    ComputeAdapter,
)
from services.compute_adapters.stub_state import get_stub_job, increment_stub_poll, register_stub_job


class AkashComputeAdapter(ComputeAdapter):
    slug = "akash"
    display_name = "Akash Network"
    network = "akash"
    mode = "stub"
    inspiration_slug = "akash"

    def submit_job(self, spec: AdapterJobSpec) -> AdapterSubmitResult:
        spec.validate()
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

    def poll_job(
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
                metadata={"poll_count": polls},
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
            metadata={"poll_count": polls, "deployment_status": "active"},
        )
