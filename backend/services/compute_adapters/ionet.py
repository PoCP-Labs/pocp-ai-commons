"""io.net GPU network adapter — stub v0.1."""

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


class IoNetComputeAdapter(ComputeAdapter):
    slug = "io-net"
    display_name = "io.net"
    network = "io.net"
    mode = "stub"
    inspiration_slug = "io-net"

    def submit_job(self, spec: AdapterJobSpec) -> AdapterSubmitResult:
        spec.validate()
        external_job_id = f"ionet-stub-{uuid.uuid4().hex[:12]}"
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
            metadata={"cluster_mode": "stub", "gpu_network": True},
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
                error=f"unknown io.net job: {external_job_id}",
            )
        polls = increment_stub_poll(external_job_id)
        if polls < 2:
            return AdapterPollResult(status=AdapterJobStatus.running, metadata={"poll_count": polls})
        gpu_count = 1
        if context and context.get("gpu_count") is not None:
            gpu_count = int(context["gpu_count"])
        return AdapterPollResult(
            status=AdapterJobStatus.succeeded,
            output_material="[PoCP io.net stub] Distributed GPU inference job complete.",
            resource_units={
                "gpu_seconds": float(gpu_count) * 2.0,
                "gpu_count": gpu_count,
                "network": "io.net",
                "currency_note": "IO settlement external to PoCP ledger",
            },
            metadata={"poll_count": polls},
        )
