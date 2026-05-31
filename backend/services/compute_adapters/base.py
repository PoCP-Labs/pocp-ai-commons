"""Compute adapter contract — external GPU/cloud networks as PoCP Compute Entities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from services.compute_receipt import build_compute_receipt

VALID_ADAPTER_CAPABILITIES = frozenset(
    {
        "llm_inference",
        "embeddings",
        "witness",
        "mcp_host",
        "agent_runtime",
        "training",
    }
)


class AdapterJobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


@dataclass
class AdapterJobSpec:
    capability: str
    requester_entity_id: str
    provider_entity_id: str
    contribution_id: str | None = None
    task_id: str | None = None
    trace_id: str | None = None
    constraints: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.contribution_id and not self.task_id:
            raise ValueError("contribution_id or task_id required for contribution-bound compute")
        cap = self.capability.strip()
        if cap not in VALID_ADAPTER_CAPABILITIES:
            raise ValueError(
                f"invalid capability {cap!r}; "
                f"must be one of: {', '.join(sorted(VALID_ADAPTER_CAPABILITIES))}"
            )
        if not self.requester_entity_id:
            raise ValueError("requester_entity_id is required")
        if not self.provider_entity_id:
            raise ValueError("provider_entity_id is required")


@dataclass
class AdapterSubmitResult:
    external_job_id: str
    status: AdapterJobStatus
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterPollResult:
    status: AdapterJobStatus
    output_material: str | None = None
    resource_units: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ComputeAdapter(ABC):
    slug: str
    display_name: str
    network: str
    mode: str = "stub"
    inspiration_slug: str | None = None

    def catalog_entry(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "display_name": self.display_name,
            "network": self.network,
            "mode": self.mode,
            "inspiration_slug": self.inspiration_slug,
            "spec_doc": "docs/COMPUTE-ADAPTER-SPEC.md",
        }

    def quote_job(self, spec: AdapterJobSpec) -> dict[str, Any]:
        """Advisory estimate — no billing commitment."""
        spec.validate()
        return {
            "adapter": self.slug,
            "capability": spec.capability,
            "estimated_latency_ms": 5000 if self.mode == "stub" else None,
            "advisory_only": True,
            "note": "External network tokens are not PoCP settlement currency.",
        }

    @abstractmethod
    def submit_job(self, spec: AdapterJobSpec) -> AdapterSubmitResult: ...

    @abstractmethod
    def poll_job(
        self,
        external_job_id: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> AdapterPollResult: ...

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
        started = started_at or datetime.now(timezone.utc)
        finished = finished_at or datetime.now(timezone.utc)
        latency_ms = int(max((finished - started).total_seconds() * 1000, 0))
        return build_compute_receipt(
            provider_entity_id=spec.provider_entity_id,
            provider_node_id=None,
            capability=spec.capability,
            adapter=self.slug,
            model=spec.constraints.get("model"),
            contribution_id=spec.contribution_id,
            task_id=spec.task_id,
            job_id=job_id,
            initiator_entity_id=spec.requester_entity_id,
            input_material=input_material or spec.constraints.get("input_preview"),
            output_material=poll.output_material,
            latency_ms=latency_ms,
            started_at=started,
            finished_at=finished,
            extra={
                "external_job_id": external_job_id,
                "adapter_mode": self.mode,
                "network": self.network,
                "resource_units": poll.resource_units,
                "trace_id": spec.trace_id,
                **(poll.metadata or {}),
            },
        )

    def map_failure(self, error: str) -> dict[str, Any]:
        return {
            "error": (error or "adapter failure")[:500],
            "adapter": self.slug,
            "federation_safe": True,
        }
