"""Import approved contribution events from trusted peer nodes."""

import os

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.entity import Entity, EntityType
from models.federation import FederatedImport
from models.wallet import ReputationScore
from services.reputation_audit import record_reputation_audit
from schemas.federation import ImportEventPayload, TrustedNode
from services.entity_portable import resolve_or_create_portable_entity
from services.evidence import POCP_META_KEY, hash_evidence
from services.federation_crypto import import_payload_message, verify_message
from services.crypto_suite import verify_federation_signatures
from services.ledger_chain import append_ledger_record
from services.proof import compute_contribution_proof_hash
from services.protocol_config import get_rewards_config
from services.trust_config import trusted_nodes_map as _trusted_nodes_map


def _trust_weight(source_node_id: str) -> float:
    nodes = _trusted_nodes_map()
    node = nodes.get(source_node_id)
    if node:
        return float(node.trust_weight)
    cfg = get_rewards_config().get("federation", {})
    return float(os.getenv("POCP_FEDERATION_TRUST_WEIGHT", cfg.get("default_trust_weight", 0.5)))


def _add_reputation(
    db: Session,
    entity_id: str,
    amount: float,
    category: str,
    *,
    reference_id: str | None = None,
) -> None:
    rep = (
        db.query(ReputationScore)
        .filter(ReputationScore.entity_id == entity_id, ReputationScore.category == category)
        .first()
    )
    if rep is None:
        rep = ReputationScore(entity_id=entity_id, score=amount, category=category)
        db.add(rep)
    else:
        rep.score += amount
    db.flush()
    record_reputation_audit(
        db,
        entity_id=entity_id,
        category=category,
        delta=amount,
        balance_after=rep.score,
        source="federation_import",
        reason="Imported approved contribution reputation",
        reference_id=reference_id,
    )


def _verify_import_signature(payload: ImportEventPayload, evidence_hash: str, trusted: dict[str, TrustedNode]) -> None:
    require_sig = os.getenv("POCP_REQUIRE_IMPORT_SIGNATURE", "false").lower() == "true"
    if not payload.signature and not require_sig:
        return

    if not payload.signature:
        raise HTTPException(status_code=400, detail="Import signature required")

    node = trusted.get(payload.source_node_id)
    public_key = node.public_key if node else None
    if not public_key:
        raise HTTPException(
            status_code=400,
            detail=f"No public_key configured for trusted node {payload.source_node_id}",
        )

    message = import_payload_message(
        source_node_id=payload.source_node_id,
        contribution_id=payload.contribution_id,
        primary_entity_portable_id=payload.primary_entity_portable_id,
        evidence_hash=evidence_hash,
        ledger_record_hash=payload.ledger_record_hash,
    )
    if not verify_message(message, payload.signature, public_key):
        raise HTTPException(status_code=400, detail="Invalid import signature")


def _verify_proof_signature(source_node_id: str, proof: dict, trusted: dict[str, TrustedNode]) -> None:
    federation = proof.get("federation") or {}
    signatures = federation.get("signatures") or {}
    classic = signatures.get("classic") or {}
    signature = federation.get("signature") or classic.get("signature")
    proof_hash = (proof.get("integrity") or {}).get("proof_hash")
    if not proof_hash:
        raise HTTPException(status_code=400, detail="Proof missing integrity.proof_hash")

    computed_hash = compute_contribution_proof_hash(proof)
    if proof_hash != computed_hash:
        raise HTTPException(status_code=400, detail="Proof hash mismatch")

    require_sig = os.getenv("POCP_REQUIRE_IMPORT_SIGNATURE", "false").lower() == "true"
    if not signature and not require_sig:
        return

    if not signature:
        raise HTTPException(status_code=400, detail="Proof federation signature required")

    if federation.get("node_id") and federation["node_id"] != source_node_id:
        raise HTTPException(status_code=400, detail="Proof node_id does not match source_node_id")

    public_key = federation.get("public_key")
    node = trusted.get(source_node_id)
    if node and node.public_key:
        public_key = node.public_key
    trusted_pqc = getattr(node, "pqc_public_key", None) if node else None

    verify_federation_signatures(
        federation,
        proof_hash,
        trusted_public_key=public_key,
        trusted_pqc_public_key=trusted_pqc,
    )


def import_federated_event(
    db: Session,
    payload: ImportEventPayload,
    *,
    proof_signature_verified: bool = False,
    protocol_excerpt: dict | None = None,
) -> FederatedImport:
    allow_untrusted = os.getenv("POCP_ALLOW_UNTRUSTED_IMPORT", "false").lower() == "true"
    trusted = _trusted_nodes_map()
    if payload.source_node_id not in trusted and not allow_untrusted:
        raise HTTPException(
            status_code=403,
            detail=f"Untrusted source node: {payload.source_node_id}",
        )

    duplicate = (
        db.query(FederatedImport)
        .filter(
            FederatedImport.source_node_id == payload.source_node_id,
            FederatedImport.source_contribution_id == payload.contribution_id,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="Contribution already imported from this source node",
        )

    evidence = dict(payload.evidence or {})
    meta = evidence.get(POCP_META_KEY) or {}
    content_hash = meta.get("content_hash") or hash_evidence(evidence)
    computed = hash_evidence({k: v for k, v in evidence.items() if k != POCP_META_KEY})
    if content_hash != computed:
        raise HTTPException(status_code=400, detail="Evidence content_hash mismatch")

    if not proof_signature_verified:
        _verify_import_signature(payload, content_hash, trusted)

    primary = resolve_or_create_portable_entity(db, payload.primary_entity_portable_id)
    trust_weight = _trust_weight(payload.source_node_id)
    defaults = get_rewards_config()["contribution_defaults"]
    human_rep_base = float(defaults["human"].get("reputation_base", 10))
    skill_rep_base = float(defaults["skill"]["reputation_base"])
    agent_rep_base = float(defaults["agent"]["reputation_base"])

    reputation_applied = 0.0
    for participant in payload.participants:
        entity = resolve_or_create_portable_entity(db, participant.entity_portable_id)
        role = participant.role
        weight = participant.weight or 1.0
        if role == "skill_provider":
            amount = round(skill_rep_base * weight * trust_weight, 2)
            _add_reputation(db, entity.id, amount, "skill", reference_id=payload.contribution_id)
            reputation_applied += amount
        elif role == "executor" and entity.entity_type == EntityType.agent:
            amount = round(agent_rep_base * weight * trust_weight, 2)
            _add_reputation(db, entity.id, amount, "agent", reference_id=payload.contribution_id)
            reputation_applied += amount
        elif role in ("creator", "executor", "reviewer"):
            amount = round(human_rep_base * weight * trust_weight, 2)
            _add_reputation(db, entity.id, amount, "human", reference_id=payload.contribution_id)
            reputation_applied += amount

    if not payload.participants:
        amount = round(human_rep_base * trust_weight, 2)
        _add_reputation(db, primary.id, amount, "human", reference_id=payload.contribution_id)
        reputation_applied += amount

    stored_payload = payload.model_dump()
    if protocol_excerpt:
        stored_payload["protocol_excerpt"] = protocol_excerpt

    record = FederatedImport(
        source_node_id=payload.source_node_id,
        source_contribution_id=payload.contribution_id,
        primary_entity_id=primary.id,
        primary_portable_id=payload.primary_entity_portable_id,
        task_title=payload.task_title,
        contribution_type=payload.contribution_type,
        evidence_hash=content_hash,
        ledger_record_hash=payload.ledger_record_hash,
        trust_weight=trust_weight,
        reputation_applied=reputation_applied,
        payload=stored_payload,
    )
    db.add(record)
    db.flush()

    append_ledger_record(
        db,
        contribution_id=None,
        event_type="federation_import",
        payload={
            "federated_import_id": record.id,
            "source_node_id": payload.source_node_id,
            "source_contribution_id": payload.contribution_id,
            "primary_portable_id": payload.primary_entity_portable_id,
            "evidence_hash": content_hash,
            "ledger_record_hash": payload.ledger_record_hash,
            "trust_weight": trust_weight,
            "reputation_applied": reputation_applied,
        },
    )
    db.flush()
    return record


def import_from_proof_packet(
    db: Session,
    source_node_id: str,
    proof: dict,
    *,
    intelligence_bundle: dict | None = None,
) -> FederatedImport:
    if proof.get("proof_type") != "pocp_contribution_proof":
        raise HTTPException(status_code=400, detail="Invalid proof_type")

    event = proof.get("contribution_event") or {}
    if event.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Only approved contributions can be imported")

    allow_untrusted = os.getenv("POCP_ALLOW_UNTRUSTED_IMPORT", "false").lower() == "true"
    trusted = _trusted_nodes_map()
    if source_node_id not in trusted and not allow_untrusted:
        raise HTTPException(status_code=403, detail=f"Untrusted source node: {source_node_id}")

    _verify_proof_signature(source_node_id, proof, trusted)

    if os.getenv("POCP_VERIFY_REMOTE_LEDGER", "true").lower() == "true":
        peer = trusted.get(source_node_id)
        if peer:
            from services.federation_peers import verify_remote_ledger_record

            ledger_hashes = (proof.get("ledger_audit") or {}).get("record_hashes") or []
            approval_hash = (
                ledger_hashes[-1]
                if ledger_hashes
                else (proof.get("integrity") or {}).get("ledger_tip_hash")
            )
            try:
                verify_remote_ledger_record(peer.base_url, approval_hash)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

    evidence = proof.get("evidence") or {}
    raw_evidence = evidence.get("raw") or {}
    primary_meta = (proof.get("entity_identity") or {}).get("primary") or {}
    primary_metadata = primary_meta.get("metadata") or {}
    portable_id = primary_metadata.get("portable_id")
    if not portable_id and primary_meta.get("name"):
        portable_id = f"federated:{primary_meta['name']}"

    participants = []
    for item in (proof.get("entity_identity") or {}).get("participants") or []:
        entity = item.get("entity") or {}
        meta = entity.get("metadata") or {}
        pid = meta.get("portable_id") or f"federated:{entity.get('name', 'unknown')}"
        participants.append(
            {
                "entity_portable_id": pid,
                "role": item.get("role", "creator"),
                "weight": item.get("weight", 0.0),
            }
        )

    ledger_hashes = (proof.get("ledger_audit") or {}).get("record_hashes") or []
    payload = ImportEventPayload(
        source_node_id=source_node_id,
        contribution_id=event["id"],
        task_title=(event.get("task") or {}).get("title") or "Imported task",
        primary_entity_portable_id=portable_id or f"federated:{event.get('primary_entity_id')}",
        contribution_type=event.get("contribution_type", "knowledge"),
        evidence=raw_evidence,
        participants=participants,
        ledger_record_hash=ledger_hashes[-1] if ledger_hashes else proof.get("integrity", {}).get("ledger_tip_hash") or "",
        signature=None,
    )
    from intelligence.federation_intel import protocol_excerpt_from_bundle

    excerpt = protocol_excerpt_from_bundle(proof, intelligence_bundle)
    return import_federated_event(db, payload, proof_signature_verified=True, protocol_excerpt=excerpt)
