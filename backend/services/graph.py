"""Build Contribution Graph from ledger, participation, and invocation data."""

from sqlalchemy.orm import Session, joinedload

from models.contribution import (
    ContributionEvent,
    ContributionParticipant,
    ContributionStatus,
)
from models.entity import Entity
from models.invocation import InvocationTrace
from models.wallet import ReputationScore, Wallet

LLM_NODE_PREFIX = "llm:"


def _llm_node_id(provider: str) -> str:
    return f"{LLM_NODE_PREFIX}{provider}"


def build_contribution_graph(db: Session) -> dict:
    entities = db.query(Entity).all()
    wallets = {w.entity_id: w for w in db.query(Wallet).all()}
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

    edges: list[dict] = []
    entity_map = {e.id: e for e in entities}

    for e in entities:
        if e.owner_id and e.owner_id in entity_map:
            edges.append(
                {
                    "source": e.owner_id,
                    "target": e.id,
                    "relation": "owns",
                    "contribution_id": None,
                    "weight": 1.0,
                }
            )
        if e.creator_id and e.creator_id != e.owner_id and e.creator_id in entity_map:
            edges.append(
                {
                    "source": e.creator_id,
                    "target": e.id,
                    "relation": "created",
                    "contribution_id": None,
                    "weight": 1.0,
                }
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
    if contrib_ids:
        participants = (
            db.query(ContributionParticipant)
            .filter(ContributionParticipant.contribution_id.in_(contrib_ids))
            .all()
        )
        for p in participants:
            contrib = next((c for c in contributions if c.id == p.contribution_id), None)
            if contrib is None:
                continue
            edges.append(
                {
                    "source": p.entity_id,
                    "target": contrib.primary_entity_id,
                    "relation": p.role.value,
                    "contribution_id": p.contribution_id,
                    "weight": p.weight,
                }
            )

    traces = (
        db.query(InvocationTrace)
        .options(joinedload(InvocationTrace.steps))
        .all()
    )
    for trace in traces:
        for step in trace.steps:
            edges.append(
                {
                    "source": step.source_entity_id,
                    "target": step.target_entity_id,
                    "relation": step.action,
                    "contribution_id": trace.contribution_id,
                    "weight": 1.0,
                }
            )
            if step.action == "invokes_llm" and trace.model_provider:
                llm_id = _llm_node_id(trace.model_provider)
                if llm_id not in node_ids:
                    nodes.append(
                        {
                            "id": llm_id,
                            "entity_type": "llm",
                            "name": trace.model_provider,
                            "reputation": 0,
                            "cp_balance": 0,
                            "ai_credits": 0,
                        }
                    )
                    node_ids.add(llm_id)
                edges.append(
                    {
                        "source": step.source_entity_id,
                        "target": llm_id,
                        "relation": "invokes_llm",
                        "contribution_id": trace.contribution_id,
                        "weight": 1.0,
                    }
                )

    return {"nodes": nodes, "edges": edges}
