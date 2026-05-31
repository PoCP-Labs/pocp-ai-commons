"""Gensyn training adapter — stub v0.1 (training capability jobs)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from services.compute_adapters.base import (
    AdapterJobSpec,
    AdapterJobStatus,
    AdapterPollResult,
    AdapterSubmitResult,
    ComputeAdapter,
)
from services.compute_adapters.stub_state import get_stub_job, increment_stub_poll, register_stub_job
from services.compute_receipt import build_compute_receipt


class GensynComputeAdapter(ComputeAdapter):
    slug = "gensyn"
    display_name = "Gensyn (training attestation)"
    network = "gensyn"
    mode = "stub"
    inspiration_slug = "gensyn"

    def submit_job(self, spec: AdapterJobSpec) -> AdapterSubmitResult:
        spec.validate()
        if spec.capability != "training":
            raise ValueError("gensyn adapter only supports capability=training")
        external_job_id = f"gensyn-stub-{uuid.uuid4().hex[:12]}"
        register_stub_job(
            external_job_id,
            spec_snapshot={
                "capability": spec.capability,
                "provider_entity_id": spec.provider_entity_id,
                "contribution_id": spec.contribution_id,
                "task_id": spec.task_id,
                "objective": spec.constraints.get("objective"),
            },
            network=self.network,
        )
        return AdapterSubmitResult(
            external_job_id=external_job_id,
            status=AdapterJobStatus.queued,
            metadata={"training_mode": "stub", "verifier_required": True},
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
                error=f"unknown Gensyn job: {external_job_id}",
            )
        polls = increment_stub_poll(external_job_id)
        if polls < 3:
            return AdapterPollResult(
                status=AdapterJobStatus.running,
                metadata={"poll_count": polls, "phase": "training" if polls == 1 else "verification"},
            )

        objective = (context or {}).get("objective") or "training_run"
        checkpoint_material = f"{external_job_id}:{objective}:{polls}"
        checkpoint_hash = hashlib.sha256(checkpoint_material.encode()).hexdigest()
        return AdapterPollResult(
            status=AdapterJobStatus.succeeded,
            output_material=f"[PoCP Gensyn stub] Training verified: {objective}",
            resource_units={
                "gpu_seconds": float((context or {}).get("gpu_seconds") or 3600),
                "gpu_count": int((context or {}).get("gpu_count") or 1),
                "network": "gensyn",
                "epochs": int((context or {}).get("epochs") or 1),
            },
            metadata={
                "poll_count": polls,
                "training_attestation": {
                    "checkpoint_hash": checkpoint_hash,
                    "verifier_status": "stub_passed",
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                },
            },
        )

    def build_receipt(
        self,
        spec: AdapterJobSpec,
        *,
        external_job_id: str,
        poll: AdapterPollResult,
        job_id: str,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        input_material: str | None = None,
    ) -> dict[str, Any]:
        receipt = super().build_receipt(
            spec,
            external_job_id=external_job_id,
            poll=poll,
            job_id=job_id,
            started_at=started_at,
            finished_at=finished_at,
            input_material=input_material,
        )
        attestation = (poll.metadata or {}).get("training_attestation") or {}
        extra = dict(receipt.get("extra") or {})
        extra["training_attestation"] = attestation
        extra["gensyn_alignment"] = "pocp.training_contribution.v0.1"
        receipt["extra"] = extra
        integrity = dict(receipt.get("integrity") or {})
        if attestation:
            integrity["training_attestation"] = attestation
        receipt["integrity"] = integrity
        return receipt
