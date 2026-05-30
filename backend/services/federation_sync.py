"""Sync approved contribution proofs from trusted peer nodes into this node."""

import json
import os
import urllib.error

from sqlalchemy.orm import Session

from schemas.federation import TrustedNode
from services.federation_import import import_from_proof_packet
from services.federation_peers import probe_peer
from services.trust_config import load_trusted_nodes


def _peers_from_env() -> list[TrustedNode]:
    mirror_raw = os.getenv("POCP_MIRROR_SOURCES", "")
    if mirror_raw.strip():
        try:
            items = json.loads(mirror_raw)
            return [TrustedNode(**item) for item in items if isinstance(item, dict) and item.get("node_id")]
        except json.JSONDecodeError:
            pass
    return load_trusted_nodes()


def _export_approved_contribution_ids(base_url: str) -> list[str]:
    from services.federation_peers import _get_json

    export = _get_json(f"{base_url.rstrip('/')}/api/v1/ledger/export")
    ids: list[str] = []
    for record in export.get("records", []):
        if record.get("event_type") != "contribution_approved":
            continue
        payload = record.get("payload") or {}
        contribution_id = payload.get("contribution_id")
        if contribution_id:
            ids.append(contribution_id)
    return ids


def sync_peer_into_db(db: Session, peer: TrustedNode) -> list[dict]:
    """Import proofs from one trusted peer into the local database."""
    results: list[dict] = []
    for contribution_id in _export_approved_contribution_ids(peer.base_url):
        try:
            proof = fetch_proof(peer.base_url, contribution_id)
            record = import_from_proof_packet(db, peer.node_id, proof)
            db.commit()
            db.refresh(record)
            results.append(
                {
                    "source_node_id": peer.node_id,
                    "contribution_id": contribution_id,
                    "status": "imported",
                    "reputation_applied": record.reputation_applied,
                }
            )
        except urllib.error.HTTPError as exc:
            if exc.code == 409:
                results.append(
                    {
                        "source_node_id": peer.node_id,
                        "contribution_id": contribution_id,
                        "status": "skipped",
                        "reason": "duplicate",
                    }
                )
                db.rollback()
            else:
                results.append(
                    {
                        "source_node_id": peer.node_id,
                        "contribution_id": contribution_id,
                        "status": "error",
                        "code": exc.code,
                        "body": exc.read().decode(),
                    }
                )
                db.rollback()
        except Exception as exc:
            results.append(
                {
                    "source_node_id": peer.node_id,
                    "contribution_id": contribution_id,
                    "status": "error",
                    "error": str(exc),
                }
            )
            db.rollback()
    return results


def sync_all_trusted_peers(db: Session, peers: list[TrustedNode] | None = None) -> dict:
    peer_list = peers if peers is not None else load_trusted_nodes()
    all_results: list[dict] = []
    peer_health: list[dict] = []

    for peer in peer_list:
        peer_health.append({"node_id": peer.node_id, **probe_peer(peer.base_url)})
        all_results.extend(sync_peer_into_db(db, peer))

    imported = sum(1 for r in all_results if r.get("status") == "imported")
    skipped = sum(1 for r in all_results if r.get("status") == "skipped")
    errors = sum(1 for r in all_results if r.get("status") == "error")

    return {
        "peers_checked": len(peer_list),
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "peer_health": peer_health,
        "results": all_results,
    }


def sync_peers_http(target_base_url: str | None = None, peers: list[TrustedNode] | None = None) -> dict:
    """HTTP-based sync (mirror node calls target's import-proof API). Used by CLI scripts."""
    import json
    from services.federation_peers import post_import_proof

    target = (target_base_url or os.getenv("POCP_MIRROR_TARGET", "http://127.0.0.1:8000")).rstrip("/")
    peer_list = peers if peers is not None else _peers_from_env()
    all_results: list[dict] = []

    for peer in peer_list:
        for contribution_id in _export_approved_contribution_ids(peer.base_url):
            try:
                proof = fetch_proof(peer.base_url, contribution_id)
                imported = post_import_proof(target, peer.node_id, proof)
                all_results.append(
                    {
                        "source_node_id": peer.node_id,
                        "contribution_id": contribution_id,
                        "status": "imported",
                        "import": imported,
                    }
                )
            except urllib.error.HTTPError as exc:
                if exc.code == 409:
                    all_results.append(
                        {
                            "source_node_id": peer.node_id,
                            "contribution_id": contribution_id,
                            "status": "skipped",
                            "reason": "duplicate",
                        }
                    )
                else:
                    all_results.append(
                        {
                            "source_node_id": peer.node_id,
                            "contribution_id": contribution_id,
                            "status": "error",
                            "code": exc.code,
                            "body": exc.read().decode(),
                        }
                    )

    return {"target": target, "results": all_results}
