"""Compute capacity reservations — time-window slot booking (v0.2 draft)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

_RESERVATIONS: dict[str, dict[str, Any]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def create_reservation(
    *,
    consumer_entity_id: str,
    provider_entity_id: str,
    capability: str,
    window_start: str,
    window_end: str,
    slots: int = 1,
    prepaid_credits: float = 0.0,
    contribution_id: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    start = _parse_iso(window_start)
    end = _parse_iso(window_end)
    if end <= start:
        raise HTTPException(status_code=400, detail="window_end must be after window_start")
    if slots < 1:
        raise HTTPException(status_code=400, detail="slots must be >= 1")

    reservation_id = str(uuid.uuid4())
    record = {
        "reservation_id": reservation_id,
        "consumer_entity_id": consumer_entity_id,
        "provider_entity_id": provider_entity_id,
        "capability": capability,
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "slots": slots,
        "prepaid_credits": prepaid_credits,
        "contribution_id": contribution_id,
        "task_id": task_id,
        "status": "active",
        "created_at": _now().isoformat(),
    }
    _RESERVATIONS[reservation_id] = record
    return record


def get_reservation(reservation_id: str) -> dict[str, Any] | None:
    return _RESERVATIONS.get(reservation_id)


def list_reservations(
    *,
    consumer_entity_id: str | None = None,
    provider_entity_id: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    items = list(_RESERVATIONS.values())
    if consumer_entity_id:
        items = [r for r in items if r.get("consumer_entity_id") == consumer_entity_id]
    if provider_entity_id:
        items = [r for r in items if r.get("provider_entity_id") == provider_entity_id]
    if status:
        items = [r for r in items if r.get("status") == status]
    return sorted(items, key=lambda r: r.get("created_at") or "", reverse=True)


def cancel_reservation(reservation_id: str, *, consumer_entity_id: str) -> dict[str, Any]:
    record = _RESERVATIONS.get(reservation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if record.get("consumer_entity_id") != consumer_entity_id:
        raise HTTPException(status_code=403, detail="Not your reservation")
    record["status"] = "cancelled"
    record["cancelled_at"] = _now().isoformat()
    return record


def clear_reservations() -> None:
    _RESERVATIONS.clear()
