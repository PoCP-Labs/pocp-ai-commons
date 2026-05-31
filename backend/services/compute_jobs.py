"""Persisted compute job store — DB-backed (Phase γ)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.compute_job import ComputeJobRecord, ComputeJobStatus


def _job_to_dict(row: ComputeJobRecord) -> dict[str, Any]:
    status = row.status.value if hasattr(row.status, "value") else str(row.status)
    return {
        "job_id": row.id,
        "spec_version": "0.1",
        "status": status,
        "capability": row.capability,
        "initiator_entity_id": row.initiator_entity_id,
        "contribution_id": row.contribution_id,
        "task_id": row.task_id,
        "constraints": row.constraints_ or {},
        "selected_provider": row.selected_provider,
        "compute_receipt": row.compute_receipt,
        "execution": row.execution_,
        "settlement": row.settlement,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "advisory_only": True,
    }


def create_job_record(
    db: Session,
    *,
    capability: str,
    initiator_entity_id: str | None,
    contribution_id: str | None,
    task_id: str | None,
    constraints: dict[str, Any] | None,
    selected_provider: dict[str, Any] | None,
    receipt: dict[str, Any] | None,
    status: str = "scheduled",
) -> dict[str, Any]:
    try:
        job_status = ComputeJobStatus(status)
    except ValueError:
        job_status = ComputeJobStatus.scheduled

    row = ComputeJobRecord(
        capability=capability,
        status=job_status,
        initiator_entity_id=initiator_entity_id,
        contribution_id=contribution_id,
        task_id=task_id,
        constraints_=constraints or {},
        selected_provider=selected_provider,
        compute_receipt=receipt,
    )
    db.add(row)
    db.flush()
    return _job_to_dict(row)


def get_job_record(db: Session, job_id: str) -> dict[str, Any]:
    row = db.get(ComputeJobRecord, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Compute job not found")
    return _job_to_dict(row)


def update_job_record(db: Session, job_id: str, **fields: Any) -> dict[str, Any]:
    row = db.get(ComputeJobRecord, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Compute job not found")

    if "status" in fields:
        try:
            row.status = ComputeJobStatus(fields["status"])
        except ValueError:
            pass
    if "compute_receipt" in fields:
        row.compute_receipt = fields["compute_receipt"]
    if "selected_provider" in fields:
        row.selected_provider = fields["selected_provider"]
    if "execution" in fields:
        row.execution_ = fields["execution"]
    if "settlement" in fields:
        row.settlement = fields["settlement"]
    if "constraints" in fields:
        row.constraints_ = fields["constraints"]

    row.updated_at = datetime.utcnow()
    db.flush()
    return _job_to_dict(row)


def list_jobs_for_contribution(db: Session, contribution_id: str) -> list[dict[str, Any]]:
    rows = (
        db.query(ComputeJobRecord)
        .filter(ComputeJobRecord.contribution_id == contribution_id)
        .order_by(ComputeJobRecord.created_at.asc())
        .all()
    )
    return [_job_to_dict(row) for row in rows]


def count_jobs_for_initiator(db: Session, entity_id: str, *, since_hours: float = 24) -> int:
    cutoff = datetime.utcnow() - timedelta(hours=since_hours)
    return (
        db.query(ComputeJobRecord)
        .filter(
            ComputeJobRecord.initiator_entity_id == entity_id,
            ComputeJobRecord.created_at >= cutoff,
        )
        .count()
    )


def count_recent_jobs_for_provider(
    db: Session, provider_entity_id: str, *, since_hours: float = 1.0
) -> int:
    cutoff = datetime.utcnow() - timedelta(hours=since_hours)
    rows = (
        db.query(ComputeJobRecord)
        .filter(ComputeJobRecord.created_at >= cutoff)
        .all()
    )
    count = 0
    for row in rows:
        selected = row.selected_provider or {}
        if selected.get("provider_entity_id") == provider_entity_id:
            count += 1
    return count


def list_recent_jobs(db: Session, *, since_hours: float = 24, limit: int = 100) -> list[dict[str, Any]]:
    cutoff = datetime.utcnow() - timedelta(hours=since_hours)
    rows = (
        db.query(ComputeJobRecord)
        .filter(ComputeJobRecord.created_at >= cutoff)
        .order_by(ComputeJobRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_job_to_dict(row) for row in rows]


def clear_job_store(db: Session) -> None:
    """Test helper — delete all compute jobs."""
    db.query(ComputeJobRecord).delete()
    db.flush()
