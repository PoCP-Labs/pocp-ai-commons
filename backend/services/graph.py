"""Build Contribution Graph from ledger, participation, and invocation data."""

from sqlalchemy.orm import Session, joinedload

from models.contribution import (
    ContributionEvent,
    ContributionParticipant,
    ContributionStatus,
    ParticipantRole,
)
from genesis import RAIN_ID
from models.entity import Entity, EntityType
from models.invocation import InvocationTrace
from models.ledger import LedgerRecord
from models.wallet import ReputationScore, Wallet

CONTRIBUTION_HUB_PREFIX = "contribution:"
LEDGER_NODE_PREFIX = "ledger:"
EXCHANGE_NODE_PREFIX = "exchange:"

# Participant roles shown on the invocation chain instead of separate hub edges.
_INVOCATION_COVERED_ROLES = {ParticipantRole.executor, ParticipantRole.skill_provider}

# Roles that point from participant entity toward the contribution hub.
_HUB_INBOUND_ROLES = {
    ParticipantRole.creator: "submits",
    ParticipantRole.witness: "witnesses",
    ParticipantRole.verifier: "verifies",
    ParticipantRole.reviewer: "reviews",
    ParticipantRole.sponsor: "sponsors",
    ParticipantRole.tool_provider: "provides_tool",
    ParticipantRole.data_provider: "provides_data",
}
def _contribution_hub_id(contribution_id: str) -> str:
    return f"{CONTRIBUTION_HUB_PREFIX}{contribution_id}"


def _exchange_node_id(exchange_id: str) -> str:
    return f"{EXCHANGE_NODE_PREFIX}{exchange_id}"


def _exchange_upgrade_from_evidence(evidence: dict | None) -> dict:
    if not evidence:
        return {}
    direct = evidence.get("exchange_upgrade") or {}
    if direct.get("exchange_id"):
        return direct
    meta = evidence.get("_pocp") or {}
    nested = meta.get("exchange_upgrade") or {}
    return nested if nested.get("exchange_id") else {}


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
        if (
            e.entity_type == EntityType.organization
            and e.owner_id == RAIN_ID
            and RAIN_ID in entity_map
        ):
            _append_edge(
                edges,
                {
                    "source": RAIN_ID,
                    "target": e.id,
                    "relation": "founded",
                    "contribution_id": None,
                    "weight": 1.0,
                },
            )
            _append_edge(
                edges,
                {
                    "source": RAIN_ID,
                    "target": e.id,
                    "relation": "sponsors",
                    "contribution_id": None,
                    "weight": 1.0,
                },
            )

    contributions = (
        db.query(ContributionEvent)
        .options(
            joinedload(ContributionEvent.ai_verifications),
            joinedload(ContributionEvent.human_reviews),
        )
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

    for contrib in contributions:
        hub_id = _contribution_hub_id(contrib.id)
        if hub_id not in node_ids:
            continue
        for verification in contrib.ai_verifications:
            llm_id = llm_entities_by_name.get((verification.model_provider or "").strip().lower())
            if llm_id:
                _append_edge(
                    edges,
                    {
                        "source": llm_id,
                        "target": hub_id,
                        "relation": "witnesses",
                        "contribution_id": contrib.id,
                        "weight": verification.score or 0.0,
                    },
                )
        for review in contrib.human_reviews:
            if review.approved and review.reviewer_id in node_ids:
                _append_edge(
                    edges,
                    {
                        "source": review.reviewer_id,
                        "target": hub_id,
                        "relation": "final_review",
                        "contribution_id": contrib.id,
                        "weight": 1.0,
                    },
                )

    for contrib in contributions:
        upgrade = _exchange_upgrade_from_evidence(contrib.evidence)
        exchange_id = upgrade.get("exchange_id")
        if not exchange_id:
            continue
        ex_node = _exchange_node_id(exchange_id)
        if ex_node not in node_ids:
            kind = upgrade.get("exchange_kind") or "exchange"
            nodes.append(
                {
                    "id": ex_node,
                    "entity_type": "exchange",
                    "name": f"{kind} {exchange_id[:12]}…",
                    "reputation": 0,
                    "cp_balance": 0,
                    "ai_credits": 0,
                }
            )
            node_ids.add(ex_node)
        hub_id = _contribution_hub_id(contrib.id)
        if hub_id not in node_ids:
            continue
        _append_edge(
            edges,
            {
                "source": ex_node,
                "target": hub_id,
                "relation": "promoted_to",
                "contribution_id": contrib.id,
                "weight": 1.0,
            },
        )
        consumer_id = upgrade.get("consumer_entity_id")
        if consumer_id and consumer_id in node_ids:
            _append_edge(
                edges,
                {
                    "source": consumer_id,
                    "target": ex_node,
                    "relation": "settled_exchange",
                    "contribution_id": contrib.id,
                    "weight": 1.0,
                },
            )

    if contrib_ids:
        ledger_rows = (
            db.query(LedgerRecord)
            .filter(LedgerRecord.contribution_id.in_(contrib_ids))
            .order_by(LedgerRecord.created_at)
            .all()
        )
        for record in ledger_rows:
            ledger_node_id = f"{LEDGER_NODE_PREFIX}{record.id}"
            if ledger_node_id not in node_ids:
                nodes.append(
                    {
                        "id": ledger_node_id,
                        "entity_type": "ledger",
                        "name": record.event_type.replace("_", " ")[:24],
                        "reputation": 0,
                        "cp_balance": 0,
                        "ai_credits": 0,
                    }
                )
                node_ids.add(ledger_node_id)
            hub_id = _contribution_hub_id(record.contribution_id)
            if hub_id in node_ids:
                _append_edge(
                    edges,
                    {
                        "source": hub_id,
                        "target": ledger_node_id,
                        "relation": "recorded_in",
                        "contribution_id": record.contribution_id,
                        "weight": 1.0,
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

    from services.external_inspiration import append_inspiration_graph_edges

    append_inspiration_graph_edges(
        db,
        edges=edges,
        nodes=nodes,
        node_ids=node_ids,
        entity_map=entity_map,
        contributions=contributions,
        append_edge=_append_edge,
    )

    from services.federation_community import append_federation_peer_graph_edges

    append_federation_peer_graph_edges(
        db,
        edges=edges,
        entity_map=entity_map,
        append_edge=_append_edge,
    )

    from services.federation_community import append_federated_import_graph_edges

    append_federated_import_graph_edges(
        db,
        nodes=nodes,
        node_ids=node_ids,
        edges=edges,
        entity_map=entity_map,
        append_edge=_append_edge,
    )

    from services.oss_entity_registry import append_oss_entity_graph_edges

    append_oss_entity_graph_edges(
        db,
        edges=edges,
        entity_map=entity_map,
        append_edge=_append_edge,
    )

    from services.community_partner import append_partner_graph_edges

    append_partner_graph_edges(
        db,
        edges=edges,
        entity_map=entity_map,
        append_edge=_append_edge,
    )

    contribution_nodes = sum(1 for n in nodes if n["entity_type"] == "contribution")
    exchange_nodes = sum(1 for n in nodes if n["entity_type"] == "exchange")
    federation_import_nodes = sum(1 for n in nodes if n["entity_type"] == "federation_import")
    ledger_nodes = sum(1 for n in nodes if n["entity_type"] == "ledger")
    return {
        "nodes": nodes,
        "edges": edges,
        "entity_count": len(entities),
        "contribution_node_count": contribution_nodes,
        "exchange_node_count": exchange_nodes,
        "federation_import_node_count": federation_import_nodes,
        "ledger_node_count": ledger_nodes,
    }
