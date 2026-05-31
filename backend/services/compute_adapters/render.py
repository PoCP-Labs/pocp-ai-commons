"""Render Network GPU adapter — stub v0.1."""

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


class RenderComputeAdapter(ComputeAdapter):
    slug = "render-network"
    display_name = "Render Network"
    network = "render"
    mode = "stub"
    inspiration_slug = "render-network"

    def submit_job(self, spec: AdapterJobSpec) -> AdapterSubmitResult:
        spec.validate()
        external_job_id = f"render-stub-{uuid.uuid4().hex[:12]}"
        register_stub_job(
            external_job_id,
            spec_snapshot={
                "capability": spec.capability,
                "provider_entity_id": spec.provider_entity_id,
            },
            network=self.network,
        )
        return AdapterSubmitResult(
            external_job_id=external_job_id,
            status=AdapterJobStatus.queued,
            metadata={"job_type": "gpu_ml_stub"},
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
                error=f"unknown Render job: {external_job_id}",
            )
        polls = increment_stub_poll(external_job_id)
        if polls < 2:
            return AdapterPollResult(status=AdapterJobStatus.running, metadata={"poll_count": polls})
        return AdapterPollResult(
            status=AdapterJobStatus.succeeded,
            output_material="[PoCP Render stub] GPU frame/compute job finished.",
            resource_units={
                "gpu_seconds": 2.0,
                "network": "render",
                "currency_note": "RNDR settlement external to PoCP ledger",
            },
            metadata={"poll_count": polls},
        )
