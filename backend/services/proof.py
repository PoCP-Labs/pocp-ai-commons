"""Contribution proof packet builder.

This module turns PoCP's core protocol layers into one portable object:
Entity identity, Contribution Event, Evidence, Verification, Graph links,
Rights/Reputation, and Ledger audit.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session, joinedload

from models.contribution import ContributionEvent
from models.entity import Entity
from models.invocation import InvocationTrace
from models.ledger import LedgerRecord
from models.wallet import CreditTransaction, ReputationScore, Wallet
from services.evidence import POCP_META_KEY, evidence_types, hash_evidence, standardize_evidence_items
from services.federation_crypto import get_node_public_key_hex, sign_message
from services.provenance import provenance_from_evidence
from services.attribution_merkle import build_attribution_merkle_proof
from services.code_attribution_bridge import build_code_attribution_context
from services.expert_cards import expert_cards_from_contribution

POCP_PROOF_SPEC_VERSION = "0.1"
POCP_PROOF_TYPE = "pocp_contribution_proof"
POCP_PROOF_SCHEMA = "pocp.contribution_proof.v0.1"
POCP_HASH_ALGORITHM = "sha256"

PROOF_LAYER_COVERAGE = [
    "entity_identity",
    "contribution_event",
    "contribution_participant",
    "evidence_hash",
    "provenance_envelope",
    "expert_cards",
    "code_attribution_context",
    "attribution_merkle_proof",
    "human_ai_verification_state",
    "contribution_graph",
    "contribution_to_rights_conversion",
    "ledger_memory",
]


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return value


def _stable_hash(payload: dict) -> str:
    stable_payload = dict(payload)
    stable_payload.pop("generated_at", None)
    stable_payload.pop("federation", None)
    if isinstance(stable_payload.get("integrity"), dict):
        integrity = dict(stable_payload["integrity"])
        integrity.pop("proof_hash", None)
        stable_payload["integrity"] = integrity
    material = json.dumps(_jsonable(stable_payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def compute_contribution_proof_hash(proof: dict) -> str:
    """Recompute a proof hash using the PoCP v0.1 canonicalization rule."""
    return _stable_hash(proof)


def _entity_snapshot(entity: Entity | None) -> dict | None:
    if entity is None:
        return None
    return {
        "id": entity.id,
        "entity_type": entity.entity_type.value,
        "name": entity.name,
        "description": entity.description,
        "owner_id": entity.owner_id,
        "creator_id": entity.creator_id,
        "status": entity.status.value,
        "metadata": entity.metadata_ or {},
    }


def _evidence_items(evidence: dict | None) -> list[dict]:
    return standardize_evidence_items(evidence)


def build_contribution_proof_packet(db: Session, contribution_id: str) -> dict | None:
    contribution = (
        db.query(ContributionEvent)
        .options(
            joinedload(ContributionEvent.task),
            joinedload(ContributionEvent.participants),
            joinedload(ContributionEvent.ai_verifications),
            joinedload(ContributionEvent.human_reviews),
        )
        .filter(ContributionEvent.id == contribution_id)
        .first()
    )
    if contribution is None:
        return None

    participant_ids = [p.entity_id for p in contribution.participants]
    entity_ids = set(participant_ids + [contribution.primary_entity_id])
    entities = (
        {e.id: e for e in db.query(Entity).filter(Entity.id.in_(entity_ids)).all()}
        if entity_ids
        else {}
    )

    evidence = contribution.evidence or {}
    evidence_meta = evidence.get(POCP_META_KEY) or {}
    content_hash = evidence_meta.get("content_hash") or hash_evidence(evidence)

    ledgers = (
        db.query(LedgerRecord)
        .filter(LedgerRecord.contribution_id == contribution.id)
        .order_by(LedgerRecord.created_at.asc(), LedgerRecord.id.asc())
        .all()
    )

    transactions = (
        db.query(CreditTransaction, Wallet)
        .join(Wallet, CreditTransaction.wallet_id == Wallet.id)
        .filter(CreditTransaction.contribution_id == contribution.id)
        .order_by(CreditTransaction.created_at.asc(), CreditTransaction.id.asc())
        .all()
    )

    reputation = (
        db.query(ReputationScore)
        .filter(ReputationScore.entity_id.in_(participant_ids))
        .order_by(ReputationScore.entity_id.asc(), ReputationScore.category.asc())
        .all()
        if participant_ids
        else []
    )

    invocations = (
        db.query(InvocationTrace)
        .options(joinedload(InvocationTrace.steps))
        .filter(InvocationTrace.contribution_id == contribution.id)
        .order_by(InvocationTrace.created_at.asc(), InvocationTrace.id.asc())
        .all()
    )

    graph_edges = []
    for participant in contribution.participants:
        graph_edges.append(
            {
                "source": participant.entity_id,
                "target": contribution.primary_entity_id,
                "relation": participant.role.value,
                "weight": participant.weight,
                "contribution_id": contribution.id,
            }
        )
    for trace in invocations:
        for step in trace.steps:
            graph_edges.append(
                {
                    "source": step.source_entity_id,
                    "target": step.target_entity_id,
                    "relation": step.action,
                    "weight": 1.0,
                    "contribution_id": contribution.id,
                    "invocation_id": trace.id,
                }
            )

    packet = {
        "spec_version": POCP_PROOF_SPEC_VERSION,
        "proof_type": POCP_PROOF_TYPE,
        "proof_schema": POCP_PROOF_SCHEMA,
        "proof_id": f"pocp-proof:{contribution.id}",
        "generated_at": datetime.utcnow(),
        "protocol_layers": PROOF_LAYER_COVERAGE,
        "contribution_event": {
            "id": contribution.id,
            "task": {
                "id": contribution.task.id if contribution.task else None,
                "title": contribution.task.title if contribution.task else None,
                "description": contribution.task.description if contribution.task else None,
                "sponsor_id": contribution.task.sponsor_id if contribution.task else None,
                "status": contribution.task.status.value if contribution.task else None,
            },
            "primary_entity_id": contribution.primary_entity_id,
            "contribution_type": contribution.contribution_type,
            "description": contribution.description,
            "status": contribution.status.value,
            "created_at": contribution.created_at,
        },
        "entity_identity": {
            "primary": _entity_snapshot(entities.get(contribution.primary_entity_id)),
            "participants": [
                {
                    "entity": _entity_snapshot(entities.get(participant.entity_id)),
                    "role": participant.role.value,
                    "weight": participant.weight,
                    "evidence": participant.evidence or {},
                }
                for participant in contribution.participants
            ],
        },
        "evidence": {
            "content_hash": content_hash,
            "spec_version": evidence_meta.get("spec_version"),
            "evidence_standard": evidence_meta.get("evidence_standard"),
            "evidence_types": evidence_meta.get("evidence_types") or evidence_types(evidence),
            "provenance": provenance_from_evidence(evidence),
            "items": _evidence_items(evidence),
            "raw": evidence,
        },
        "expert_cards": expert_cards_from_contribution(db, contribution),
        "code_attribution_context": build_code_attribution_context(evidence),
        "attribution_merkle_proof": build_attribution_merkle_proof(evidence),
        "verification": {
            "ai_advisory": [
                {
                    "id": result.id,
                    "model_provider": result.model_provider,
                    "score": result.score,
                    "passed": result.passed,
                    "feedback": result.feedback,
                    "created_at": result.created_at,
                }
                for result in contribution.ai_verifications
            ],
            "human_reviews": [
                {
                    "id": review.id,
                    "reviewer_id": review.reviewer_id,
                    "approved": review.approved,
                    "feedback": review.feedback,
                    "created_at": review.created_at,
                }
                for review in contribution.human_reviews
            ],
            "rule": "AI advises; humans approve; ledger remembers.",
        },
        "contribution_graph": {
            "nodes": [_entity_snapshot(e) for e in entities.values()],
            "edges": graph_edges,
            "invocations": [
                {
                    "id": trace.id,
                    "initiator_id": trace.initiator_id,
                    "task_id": trace.task_id,
                    "model_provider": trace.model_provider,
                    "status": trace.status.value,
                    "created_at": trace.created_at,
                    "steps": [
                        {
                            "step_order": step.step_order,
                            "source_entity_id": step.source_entity_id,
                            "target_entity_id": step.target_entity_id,
                            "action": step.action,
                        }
                        for step in trace.steps
                    ],
                }
                for trace in invocations
            ],
        },
        "rights_and_reputation": {
            "credit_transactions": [
                {
                    "id": tx.id,
                    "entity_id": wallet.entity_id,
                    "wallet_id": wallet.id,
                    "amount": tx.amount,
                    "credit_type": tx.credit_type.value,
                    "right_kind": "bc" if tx.credit_type.value == "ai_credits" else "cp",
                    "spendable": tx.credit_type.value == "ai_credits",
                    "transferable": False,
                    "reason": tx.reason,
                    "created_at": tx.created_at,
                }
                for tx, wallet in transactions
            ],
            "current_reputation": [
                {
                    "entity_id": item.entity_id,
                    "category": item.category,
                    "score": item.score,
                    "updated_at": item.updated_at,
                }
                for item in reputation
            ],
        },
        "ledger_audit": {
            "records": [
                {
                    "id": record.id,
                    "event_type": record.event_type,
                    "payload": record.payload or {},
                    "prev_hash": record.prev_hash,
                    "record_hash": record.record_hash,
                    "created_at": record.created_at,
                }
                for record in ledgers
            ],
            "record_hashes": [record.record_hash for record in ledgers if record.record_hash],
        },
    }

    packet["integrity"] = {
        "evidence_hash": content_hash,
        "ledger_tip_hash": packet["ledger_audit"]["record_hashes"][-1]
        if packet["ledger_audit"]["record_hashes"]
        else None,
        "hash_algorithm": POCP_HASH_ALGORITHM,
        "canonicalization": "json-sort-keys-compact-excludes-generated_at-federation-proof_hash",
    }
    packet["integrity"]["proof_hash"] = _stable_hash(packet)

    public_key = get_node_public_key_hex()
    proof_hash = packet["integrity"]["proof_hash"]
    signature = sign_message(proof_hash) if public_key else None
    if public_key and signature:
        packet["federation"] = {
            "node_id": os.getenv("POCP_NODE_ID", "unknown"),
            "public_key": public_key,
            "signature": signature,
            "signed_field": "integrity.proof_hash",
        }

    return _jsonable(packet)
