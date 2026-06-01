"""Build per-entity connection views across structural, protocol, and operational layers."""

from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session, joinedload

from intelligence.entity_ontology import (
    CONNECTION_ENTRYPOINTS,
    connection_matrix_document,
    connection_spec_for,
    invocation_action_for,
)
from models.contribution import ContributionParticipant
from models.entity import Entity
from models.invocation import InvocationStep, InvocationTrace


def _entity_brief(entity: Entity | None) -> dict[str, Any] | None:
    if entity is None:
        return None
    return {
        "entity_id": entity.id,
        "entity_type": entity.entity_type.value,
        "name": entity.name,
        "status": entity.status.value,
    }


def _step_brief(step: InvocationStep, entity_map: dict[str, Entity]) -> dict[str, Any]:
    source = entity_map.get(step.source_entity_id)
    target = entity_map.get(step.target_entity_id)
    return {
        "step_id": step.id,
        "trace_id": step.trace_id,
        "step_order": step.step_order,
        "action": step.action,
        "source": _entity_brief(source),
        "target": _entity_brief(target),
        "has_capability_receipt": bool((step.metadata_ or {}).get("capability_receipt")),
    }


def _aggregate_by_type(entity_ids: list[str], entity_map: dict[str, Entity]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for eid in entity_ids:
        entity = entity_map.get(eid)
        if entity:
            counts[entity.entity_type.value] += 1
    return dict(sorted(counts.items()))


def build_entity_connections(
    db: Session,
    entity_id: str,
    *,
    limit: int = 50,
) -> dict[str, Any] | None:
    """Return three-layer connection slice for one entity instance."""
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        return None

    et = entity.entity_type.value
    spec = connection_spec_for(et)

    owned = (
        db.query(Entity)
        .filter(Entity.owner_id == entity_id)
        .order_by(Entity.name)
        .limit(limit)
        .all()
    )
    created = (
        db.query(Entity)
        .filter(Entity.creator_id == entity_id, Entity.id != entity_id)
        .order_by(Entity.name)
        .limit(limit)
        .all()
    )
    owner = db.query(Entity).filter(Entity.id == entity.owner_id).first() if entity.owner_id else None

    participations = (
        db.query(ContributionParticipant)
        .filter(ContributionParticipant.entity_id == entity_id)
        .options(joinedload(ContributionParticipant.contribution))
        .order_by(ContributionParticipant.contribution_id.desc())
        .limit(limit)
        .all()
    )
    roles_seen = sorted({p.role.value for p in participations})

    out_steps = (
        db.query(InvocationStep)
        .filter(InvocationStep.source_entity_id == entity_id)
        .order_by(InvocationStep.trace_id, InvocationStep.step_order)
        .limit(limit)
        .all()
    )
    in_steps = (
        db.query(InvocationStep)
        .filter(InvocationStep.target_entity_id == entity_id)
        .order_by(InvocationStep.trace_id, InvocationStep.step_order)
        .limit(limit)
        .all()
    )
    traces_initiated = (
        db.query(InvocationTrace).filter(InvocationTrace.initiator_id == entity_id).count()
    )

    related_ids = {entity_id}
    for e in owned + created + ([owner] if owner else []):
        related_ids.add(e.id)
    for step in out_steps + in_steps:
        related_ids.add(step.source_entity_id)
        related_ids.add(step.target_entity_id)
    entity_map = {
        e.id: e for e in db.query(Entity).filter(Entity.id.in_(related_ids)).all()
    }

    outbound_targets = _aggregate_by_type(
        [s.target_entity_id for s in out_steps], entity_map
    )
    inbound_sources = _aggregate_by_type(
        [s.source_entity_id for s in in_steps], entity_map
    )

    allowed_targets = spec.get("typical_invocation_targets", [])
    suggested_actions = {
        target: invocation_action_for(et, target)
        for target in allowed_targets
        if invocation_action_for(et, target)
    }

    return {
        "entity_id": entity_id,
        "entity_type": et,
        "name": entity.name,
        "principle": "Everything connects through verified contribution.",
        "principle_zh": "万物都有贡献，万物互联于贡献协议。",
        "connection_spec": spec,
        "allowed": {
            "can_own_types": spec.get("can_own", []),
            "typical_invocation_targets": allowed_targets,
            "suggested_invocation_actions": suggested_actions,
            "typical_participant_roles": spec.get("typical_participant_roles", []),
            "connect_via": spec.get("connect_via", []),
        },
        "structural": {
            "owner": _entity_brief(owner),
            "owned_count": db.query(Entity).filter(Entity.owner_id == entity_id).count(),
            "owned": [_entity_brief(e) for e in owned],
            "created_count": db.query(Entity)
            .filter(Entity.creator_id == entity_id, Entity.id != entity_id)
            .count(),
            "created": [_entity_brief(e) for e in created],
        },
        "protocol": {
            "participation_count": db.query(ContributionParticipant)
            .filter(ContributionParticipant.entity_id == entity_id)
            .count(),
            "roles_seen": roles_seen,
            "participations": [
                {
                    "contribution_id": p.contribution_id,
                    "role": p.role.value,
                    "weight": p.weight,
                    "contribution_status": p.contribution.status.value
                    if p.contribution
                    else None,
                }
                for p in participations
            ],
        },
        "operational": {
            "traces_initiated_count": traces_initiated,
            "outbound_step_count": db.query(InvocationStep)
            .filter(InvocationStep.source_entity_id == entity_id)
            .count(),
            "inbound_step_count": db.query(InvocationStep)
            .filter(InvocationStep.target_entity_id == entity_id)
            .count(),
            "outbound_by_target_type": outbound_targets,
            "inbound_by_source_type": inbound_sources,
            "outbound_steps": [_step_brief(s, entity_map) for s in out_steps],
            "inbound_steps": [_step_brief(s, entity_map) for s in in_steps],
        },
        "entrypoints": CONNECTION_ENTRYPOINTS.get(et, {}),
        "docs": "docs/protocol/ENTITY-CONNECTION.md",
        "matrix_api": "/api/v1/entities/connections/matrix",
    }


def entity_connection_matrix() -> dict[str, Any]:
    """Full type-level connection catalog (protocol layer)."""
    return connection_matrix_document()
