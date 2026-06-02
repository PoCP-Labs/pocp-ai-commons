"""Federation overlay relay — fetch peer proofs, validate, enqueue ProtocolEvents, optional import."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from services.federation_import import import_from_proof_packet
from services.federation_peers import fetch_proof as fetch_peer_proof_http
from services.network.protocol_bridge import protocol_event_to_dict
from services.network.runtime import enqueue_event
from services.network.types import ProtocolEvent
from services.trust_config import trusted_nodes_map
from services.trust_policy_bundle import validate_proof_against_trust_policy


def resolve_trusted_peer(source_node_id: str) -> dict[str, Any]:
    peer = trusted_nodes_map().get(source_node_id)
    if peer is None:
        raise ValueError(f"Untrusted or unknown source_node_id: {source_node_id}")
    return {
        "node_id": peer.node_id,
        "base_url": peer.base_url.rstrip("/"),
        "trust_weight": float(peer.trust_weight),
    }


def fetch_proof_from_peer(source_node_id: str, contribution_id: str) -> dict[str, Any]:
    peer = resolve_trusted_peer(source_node_id)
    proof = fetch_peer_proof_http(peer["base_url"], contribution_id)
    if not isinstance(proof, dict):
        raise ValueError("Peer returned invalid proof payload")
    return proof


def enqueue_federated_proof_offered(
    *,
    source_node_id: str,
    contribution_id: str,
    proof: dict,
    validation: dict[str, Any],
    dialogue_id: str | None = None,
) -> dict[str, Any]:
    proof_hash = (proof.get("integrity") or {}).get("proof_hash")
    event = ProtocolEvent.create(
        "FederatedProofOffered",
        {
            "source_node_id": source_node_id,
            "contribution_id": contribution_id,
            "proof_hash": proof_hash,
            "trust_policy_valid": validation.get("blocking_valid"),
            "dialogue_id": dialogue_id,
        },
        node_id=source_node_id,
    )
    return enqueue_event(event)


def relay_federation_offer(
    db: Session,
    *,
    source_node_id: str,
    contribution_id: str | None = None,
    proof: dict | None = None,
    auto_import: bool = False,
    dialogue_id: str | None = None,
) -> dict[str, Any]:
    """
    PN-4: Pull proof from trusted peer (or use inline), validate, overlay enqueue, optional import.
    """
    peer = resolve_trusted_peer(source_node_id)

    if proof is None:
        if not contribution_id:
            raise ValueError("contribution_id or proof required")
        proof = fetch_proof_from_peer(source_node_id, contribution_id)
    else:
        contribution_id = contribution_id or (proof.get("contribution_event") or {}).get("id")
        if not contribution_id:
            raise ValueError("proof missing contribution_event.id")

    validation = validate_proof_against_trust_policy(
        proof,
        source_node_id=source_node_id,
        raise_on_block=False,
    )

    overlay_event = enqueue_federated_proof_offered(
        source_node_id=source_node_id,
        contribution_id=contribution_id,
        proof=proof,
        validation=validation,
        dialogue_id=dialogue_id,
    )

    import_summary: dict[str, Any] | None = None
    if auto_import:
        if not validation.get("blocking_valid"):
            import_summary = {
                "imported": False,
                "reason": "trust_policy_blocking_valid is false",
            }
        else:
            record = import_from_proof_packet(db, source_node_id, proof)
            import_summary = {
                "imported": True,
                "federated_import_id": record.id,
                "primary_portable_id": record.primary_portable_id,
            }

    return {
        "mode": "federation_relay",
        "peer": peer,
        "contribution_id": contribution_id,
        "validation": validation,
        "overlay_event": overlay_event,
        "import": import_summary,
        "proof_hash": (proof.get("integrity") or {}).get("proof_hash"),
    }


def federation_accept_from_proof(
    db: Session,
    *,
    source_node_id: str,
    proof: dict,
    auto_import: bool = True,
    dialogue_id: str | None = None,
) -> dict[str, Any]:
    """federation_accept dialogue kind — validate + overlay + optional import."""
    contribution_id = (proof.get("contribution_event") or {}).get("id")
    if not contribution_id:
        raise ValueError("proof missing contribution_event.id")

    return relay_federation_offer(
        db,
        source_node_id=source_node_id,
        contribution_id=contribution_id,
        proof=proof,
        auto_import=auto_import,
        dialogue_id=dialogue_id,
    )
