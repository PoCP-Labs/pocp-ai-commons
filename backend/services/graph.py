"""Build Contribution Graph from ledger, participation, and invocation data."""

from sqlalchemy.orm import Session, joinedload

from models.contribution import (
    ContributionEvent,
    ContributionParticipant,
    ContributionStatus,
    ParticipantRole,
)
from models.entity import Entity
from models.invocation import InvocationTrace
from models.wallet import ReputationScore, Wallet

CONTRIBUTION_HUB_PREFIX = "contribution:"

# Participant roles shown on the invocation chain instead of separate hub edges.
_INVOCATION_COVERED_ROLES = {ParticipantRole.executor, ParticipantRole.skill_provider}

# Roles that point from participant entity toward the contribution hub.
_HUB_INBOUND_ROLES = {
    ParticipantRole.creator: "submits",
    ParticipantRole.verifier: "verifies",
    ParticipantRole.reviewer: "reviews",
    ParticipantRole.sponsor: "sponsors",
}
def _contribution_hub_id(contribution_id: str) -> str:
    return f"{CONTRIBUTION_HUB_PREFIX}{contribution_id}"


def _contribution_label(contrib: ContributionEvent) -> str:
    text = (contrib.description or contrib.contribution_type or "Contribution").strip()
    return text if len(text) <= 36 else f"{text[:35]}…"


def _append_edge(edges: list[dict], edge: dict) -> None:
    key = (
        edge["source"],
        edge["target"],
        edge["relation"],
        edge.get("contribution_id"),
    )
    if any(
        (
            e["source"],
            e["target"],
            e["relation"],
            e.get("contribution_id"),
        )
        == key
        for e in edges
    ):
        return
    edges.append(edge)


def build_contribution_graph(db: Session) -> dict:
    entities = db.query(Entity).all()
    wallets = {w.entity_id: w for w in db.query(Wallet).all()}
    llm_entities_by_name = {
        e.name.strip().lower(): e.id for e in entities if e.entity_type.value == "llm" and e.name
    }
    reps = {}
    for r in db.query(ReputationScore).all():
        reps[r.entity_id] = reps.get(r.entity_id, 0) + r.score

    nodes = [
        {
            "id": e.id,
            "entity_type": e.entity_type.value,
            "name": e.name,
            "reputation": round(reps.get(e.id, 0), 2),
            "cp_balance": round(wallets[e.id].cp_balance, 2) if e.id in wallets else 0,
            "ai_credits": round(wallets[e.id].ai_credits, 2) if e.id in wallets else 0,
        }
        for e in entities
    ]
    node_ids = {n["id"] for n in nodes}
    entity_map = {e.id: e for e in entities}

    edges: list[dict] = []

    for e in entities:
        if e.owner_id and e.owner_id in entity_map:
            _append_edge(
                edges,
                {
                    "source": e.owner_id,
                    "target": e.id,
                    "relation": "owns",
                    "contribution_id": None,
                    "weight": 1.0,
                },
            )
        if e.creator_id and e.creator_id != e.owner_id and e.creator_id in entity_map:
            _append_edge(
                edges,
                {
                    "source": e.creator_id,
                    "target": e.id,
                    "relation": "created",
                    "contribution_id": None,
                    "weight": 1.0,
                },
            )

    contributions = (
        db.query(ContributionEvent)
        .filter(
            ContributionEvent.status.in_(
                [
                    ContributionStatus.approved,
                    ContributionStatus.ai_verified,
                    ContributionStatus.submitted,
                ]
            )
        )
        .all()
    )
    contrib_ids = [c.id for c in contributions]
    traces = (
        db.query(InvocationTrace)
        .options(joinedload(InvocationTrace.steps))
        .all()
    )
    traced_contrib_ids = {t.contribution_id for t in traces if t.contribution_id}

    for contrib in contributions:
        hub_id = _contribution_hub_id(contrib.id)
        if hub_id not in node_ids:
            nodes.append(
                {
                    "id": hub_id,
                    "entity_type": "contribution",
                    "name": _contribution_label(contrib),
                    "reputation": 0,
                    "cp_balance": 0,
                    "ai_credits": 0,
                }
            )
            node_ids.add(hub_id)

    if contrib_ids:
        participants = (
            db.query(ContributionParticipant)
            .filter(ContributionParticipant.contribution_id.in_(contrib_ids))
            .all()
        )
        for p in participants:
            if p.role in _INVOCATION_COVERED_ROLES and p.contribution_id in traced_contrib_ids:
                continue

            relation = _HUB_INBOUND_ROLES.get(p.role)
            if relation is None:
                continue

            hub_id = _contribution_hub_id(p.contribution_id)
            _append_edge(
                edges,
                {
                    "source": p.entity_id,
                    "target": hub_id,
                    "relation": relation,
                    "contribution_id": p.contribution_id,
                    "weight": p.weight,
                },
            )

    for trace in traces:
        last_source = None
        for step in trace.steps:
            _append_edge(
                edges,
                {
                    "source": step.source_entity_id,
                    "target": step.target_entity_id,
                    "relation": step.action,
                    "contribution_id": trace.contribution_id,
                    "weight": 1.0,
                },
            )
            last_source = step.source_entity_id

        if trace.model_provider and last_source:
            llm_id = llm_entities_by_name.get(trace.model_provider.strip().lower())
            if not llm_id:
                continue
            _append_edge(
                edges,
                {
                    "source": last_source,
                    "target": llm_id,
                    "relation": "invokes_llm",
                    "contribution_id": trace.contribution_id,
                    "weight": 1.0,
                },
            )

    contribution_nodes = sum(1 for n in nodes if n["entity_type"] == "contribution")
    return {
        "nodes": nodes,
        "edges": edges,
        "entity_count": len(entities),
        "contribution_node_count": contribution_nodes,
    }
