"""A2A SendMessage → dialogue submit kind (deferred binding, PL-5).

SendMessage does not call route_dialogue synchronously; it tags the Contribution with
dialogue_kind=submit and optionally emits ProofSubmitted to the overlay mempool.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from sqlalchemy.orm import Session

from models.contribution import ContributionEvent
from services.capability.binding_to_dialogue import (
    A2A_DEFERRED_BINDING_MODE,
    A2A_SENDMESSAGE_BINDING_KEY,
    A2A_SENDMESSAGE_DIALOGUE_KIND,
)
from services.evidence import POCP_META_KEY


def _new_dialogue_id() -> str:
    from services.entity_dialogue import new_dialogue_id

    return new_dialogue_id()


def build_deferred_submit_envelope(
    *,
    dialogue_id: str,
    human_entity_id: str,
    target_entity_id: str | None,
    task_id: str,
    contribution_id: str,
    contribution_type: str,
    description: str | None,
) -> dict[str, Any]:
    """Minimal pocp.entity_dialogue.v0.1 envelope for overlay bridge (submit kind)."""
    to_ref: dict[str, Any] = {}
    if target_entity_id:
        to_ref["entity_id"] = target_entity_id
    return {
        "schema": "pocp.entity_dialogue.v0.1",
        "dialogue_id": dialogue_id,
        "kind": A2A_SENDMESSAGE_DIALOGUE_KIND,
        "from": {"entity_id": human_entity_id},
        "to": to_ref,
        "payload": {
            "task_id": task_id,
            "contribution_type": contribution_type,
            "description": description,
            "contribution_id": contribution_id,
            "binding": A2A_SENDMESSAGE_BINDING_KEY,
            "binding_mode": A2A_DEFERRED_BINDING_MODE,
        },
    }


def apply_a2a_deferred_submit_binding(
    db: Session,
    contribution: ContributionEvent,
    *,
    human_entity_id: str,
    target_entity_id: str | None,
    context_id: str | None = None,
    message_id: str | None = None,
    enqueue_overlay: bool | None = None,
) -> str:
    """Stamp contribution evidence with deferred submit dialogue binding; optional overlay."""
    dialogue_id = _new_dialogue_id()
    stored = dict(contribution.evidence or {})
    pocp_meta = dict(stored.get(POCP_META_KEY) or {})
    a2a = dict(pocp_meta.get("a2a") or {})
    pocp_meta.update(
        {
            "dialogue_id": dialogue_id,
            "dialogue_kind": A2A_SENDMESSAGE_DIALOGUE_KIND,
            "binding": A2A_SENDMESSAGE_BINDING_KEY,
            "binding_mode": A2A_DEFERRED_BINDING_MODE,
            "a2a": a2a,
        }
    )
    if context_id:
        a2a.setdefault("context_id", context_id)
    if message_id:
        a2a.setdefault("message_id", message_id)
    pocp_meta["a2a"] = a2a
    stored[POCP_META_KEY] = pocp_meta
    contribution.evidence = stored

    should_enqueue = (
        enqueue_overlay
        if enqueue_overlay is not None
        else os.getenv("POCP_A2A_DEFERRED_OVERLAY", "true").lower() == "true"
    )
    if should_enqueue:
        envelope = build_deferred_submit_envelope(
            dialogue_id=dialogue_id,
            human_entity_id=human_entity_id,
            target_entity_id=target_entity_id,
            task_id=contribution.task_id,
            contribution_id=contribution.id,
            contribution_type=contribution.contribution_type,
            description=contribution.description,
        )
        from services.network.protocol_bridge import protocol_event_from_dialogue
        from services.network.runtime import enqueue_event

        event = protocol_event_from_dialogue(envelope)
        if event is not None:
            doc = enqueue_event(event)
            pocp_meta["protocol_event_id"] = doc.get("event_id")
            stored[POCP_META_KEY] = pocp_meta
            contribution.evidence = stored

    db.flush()
    return dialogue_id
