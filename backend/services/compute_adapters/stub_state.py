"""In-memory stub job state for adapter development (not production)."""

from __future__ import annotations

from typing import Any

_STUB_JOBS: dict[str, dict[str, Any]] = {}


def reset_stub_jobs() -> None:
    _STUB_JOBS.clear()


def register_stub_job(external_job_id: str, *, spec_snapshot: dict[str, Any], network: str) -> None:
    _STUB_JOBS[external_job_id] = {
        "polls": 0,
        "spec": spec_snapshot,
        "network": network,
    }


def get_stub_job(external_job_id: str) -> dict[str, Any] | None:
    return _STUB_JOBS.get(external_job_id)


def increment_stub_poll(external_job_id: str) -> int:
    job = _STUB_JOBS.get(external_job_id)
    if job is None:
        return 0
    job["polls"] = int(job.get("polls") or 0) + 1
    return job["polls"]
