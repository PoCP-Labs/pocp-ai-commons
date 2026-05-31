"""Aggregate ComputeReceipt objects for Proof Packet compute_attribution layer."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.invocation import InvocationTrace
from services.compute_jobs import list_jobs_for_contribution
from services.compute_receipt import verify_compute_receipt


def _dedupe_receipts(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for receipt in receipts:
        if not isinstance(receipt, dict):
            continue
        key = (receipt.get("integrity") or {}).get("receipt_hash") or id(receipt)
        if key in seen:
            continue
        seen.add(str(key))
        out.append(receipt)
    return out


def collect_receipts_from_traces(invocations: list[InvocationTrace]) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for trace in invocations:
        for step in trace.steps:
            meta = step.metadata_ or {}
            cr = meta.get("compute_receipt")
            if isinstance(cr, dict):
                receipts.append(cr)
    return receipts


def build_compute_attribution_block(
    db: Session,
    contribution_id: str,
    invocations: list[InvocationTrace],
) -> dict[str, Any]:
    trace_receipts = collect_receipts_from_traces(invocations)
    job_receipts = [
        job["compute_receipt"]
        for job in list_jobs_for_contribution(db, contribution_id)
        if isinstance(job.get("compute_receipt"), dict)
    ]
    merged = _dedupe_receipts(trace_receipts + job_receipts)
    verified = [r for r in merged if verify_compute_receipt(r)]
    capabilities = sorted({r.get("capability") for r in merged if r.get("capability")})
    providers = sorted(
        {r.get("provider_entity_id") for r in merged if r.get("provider_entity_id")}
    )
    training_attestations = [
        (r.get("integrity") or {}).get("training_attestation")
        or (r.get("extra") or {}).get("training_attestation")
        for r in merged
        if r.get("capability") == "training"
    ]
    training_attestations = [a for a in training_attestations if a]
    return {
        "spec_version": "0.1",
        "contribution_id": contribution_id,
        "receipt_count": len(merged),
        "verified_count": len(verified),
        "capabilities": capabilities,
        "provider_entity_ids": providers,
        "training_attestation_count": len(training_attestations),
        "receipts": merged,
        "rule": "Distributed compute attribution — advisory receipts bound to contribution.",
    }
