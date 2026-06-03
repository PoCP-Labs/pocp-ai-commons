"""Bitcoin-inspired peer addrbook: probe scores, bans, and address relay (HTTPS overlay)."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity, EntityStatus
from services.federation_community import peer_entity_id
from services.federation_peers import probe_peer
from services.trust_config import load_trusted_nodes

logger = logging.getLogger(__name__)

PEER_ADDRBOOK_SCHEMA = "pocp.federation_peer_addrbook.v0.1"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def ban_failure_threshold() -> int:
    return max(1, _env_int("POCP_PEER_SCORE_BAN_FAILURES", 5))


def ban_seconds() -> int:
    return max(0, _env_int("POCP_PEER_BAN_SECONDS", 3600))


def addr_relay_enabled() -> bool:
    return os.getenv("POCP_PEER_ADDR_RELAY", "true").lower() in ("1", "true", "yes", "on")


def peer_maintenance_enabled() -> bool:
    return os.getenv("POCP_PEER_MAINTENANCE", "true").lower() in ("1", "true", "yes", "on")


def auto_promote_enabled() -> bool:
    return os.getenv("POCP_PEER_AUTO_PROMOTE", "true").lower() in ("1", "true", "yes", "on")


def promote_min_successes() -> int:
    return max(1, _env_int("POCP_PEER_PROMOTE_MIN_SUCCESSES", 5))


def promote_min_score() -> float:
    return max(0.5, _env_float("POCP_PEER_PROMOTE_MIN_SCORE", 0.85))


def promote_trust_weight() -> float:
    return min(1.0, max(0.1, _env_float("POCP_PEER_PROMOTE_TRUST_WEIGHT", 0.8)))


def bootstrap_url() -> str:
    return os.getenv("POCP_PEER_BOOTSTRAP_URL", "").strip()


def default_addrbook() -> dict[str, Any]:
    return {
        "schema": PEER_ADDRBOOK_SCHEMA,
        "score": 0.5,
        "success_count": 0,
        "failure_count": 0,
        "consecutive_failures": 0,
        "last_success_at": None,
        "last_failure_at": None,
        "last_latency_ms": None,
        "last_error": None,
        "ledger_valid": None,
        "banned": False,
        "banned_until": None,
        "ban_reason": None,
    }


def get_peer_addrbook(meta: dict[str, Any] | None) -> dict[str, Any]:
    raw = (meta or {}).get("peer_addrbook") or {}
    out = {**default_addrbook(), **raw}
    out["schema"] = PEER_ADDRBOOK_SCHEMA
    return out


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def is_peer_banned(meta: dict[str, Any] | None) -> bool:
    book = get_peer_addrbook(meta)
    if not book.get("banned"):
        return False
    until = _parse_iso(book.get("banned_until"))
    if until is None:
        return True
    if until <= datetime.now(timezone.utc):
        return False
    return True


def is_peer_routable(meta: dict[str, Any] | None) -> bool:
    return not is_peer_banned(meta)


def record_probe_result(
    meta: dict[str, Any] | None,
    *,
    success: bool,
    error: str | None = None,
    latency_ms: float | None = None,
    ledger_valid: bool | None = None,
) -> dict[str, Any]:
    """Update addrbook after a probe attempt. Returns new peer_addrbook dict."""
    book = get_peer_addrbook(meta)
    now = datetime.now(timezone.utc).isoformat()

    if success:
        book["success_count"] = int(book.get("success_count") or 0) + 1
        book["consecutive_failures"] = 0
        book["last_success_at"] = now
        book["last_error"] = None
        if latency_ms is not None:
            book["last_latency_ms"] = round(float(latency_ms), 1)
        if ledger_valid is not None:
            book["ledger_valid"] = bool(ledger_valid)
        delta = 0.1 if ledger_valid is not False else 0.05
        book["score"] = min(1.0, float(book.get("score") or 0.5) + delta)
        if book.get("banned") and book.get("ban_reason") == "probe_failures":
            book["banned"] = False
            book["banned_until"] = None
            book["ban_reason"] = None
    else:
        book["failure_count"] = int(book.get("failure_count") or 0) + 1
        book["consecutive_failures"] = int(book.get("consecutive_failures") or 0) + 1
        book["last_failure_at"] = now
        book["last_error"] = (error or "probe failed")[:500]
        book["score"] = max(0.0, float(book.get("score") or 0.5) - 0.15)
        if int(book["consecutive_failures"]) >= ban_failure_threshold():
            book["banned"] = True
            book["ban_reason"] = "probe_failures"
            secs = ban_seconds()
            book["banned_until"] = (
                None if secs <= 0 else (datetime.now(timezone.utc) + timedelta(seconds=secs)).isoformat()
            )

    book["schema"] = PEER_ADDRBOOK_SCHEMA
    return book


def apply_addrbook_to_entity(entity: Entity, book: dict[str, Any]) -> None:
    meta = dict(entity.metadata_ or {})
    meta["peer_addrbook"] = book
    entity.metadata_ = meta


def extract_known_peer_urls(manifest: dict[str, Any]) -> list[str]:
    """Parse getaddr-style peer URLs from a remote manifest."""
    urls: list[str] = []
    for entry in manifest.get("known_peers") or []:
        if isinstance(entry, str) and entry.strip():
            urls.append(entry.strip().rstrip("/"))
        elif isinstance(entry, dict):
            url = (entry.get("base_url") or entry.get("url") or "").strip().rstrip("/")
            if url:
                urls.append(url)
    discovery = manifest.get("discovery") or {}
    for entry in discovery.get("known_peers") or []:
        if isinstance(entry, str) and entry.strip():
            urls.append(entry.strip().rstrip("/"))
        elif isinstance(entry, dict):
            url = (entry.get("base_url") or entry.get("url") or "").strip().rstrip("/")
            if url:
                urls.append(url)
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        out.append(url)
    return out


def collect_known_peers_for_manifest(db: Session, *, limit: int = 32) -> list[dict[str, Any]]:
    """Publish peer addresses for addr relay (Bitcoin getaddr analogue)."""
    local_node_id = os.getenv("POCP_NODE_ID", "pocp-node-local")
    local_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    peers: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()

    for peer in load_trusted_nodes():
        if peer.node_id == local_node_id or peer.node_id in seen_nodes:
            continue
        seen_nodes.add(peer.node_id)
        peers.append(
            {
                "node_id": peer.node_id,
                "base_url": peer.base_url.rstrip("/"),
                "source": "trusted",
                "trust_weight": float(peer.trust_weight),
            }
        )

    for row in db.query(Entity).filter(Entity.status == EntityStatus.active).all():
        meta = row.metadata_ or {}
        roles = meta.get("roles") or []
        if "discovered_peer" not in roles and "federation_peer" not in roles:
            continue
        node_id = meta.get("node_id") or ""
        if not node_id or node_id == local_node_id or node_id in seen_nodes:
            continue
        if is_peer_banned(meta):
            continue
        book = get_peer_addrbook(meta)
        if float(book.get("score") or 0) < 0.2:
            continue
        seen_nodes.add(node_id)
        peers.append(
            {
                "node_id": node_id,
                "base_url": meta.get("public_base_url") or meta.get("base_url"),
                "source": "discovered",
                "peer_score": float(book.get("score") or 0.5),
            }
        )
        if len(peers) >= limit:
            break

    return peers[:limit]


def gather_relay_candidate_urls(db: Session, *, limit: int = 24) -> list[str]:
    """Fetch known_peers from connected manifests (addr relay)."""
    if not addr_relay_enabled():
        return []

    from services.federation_peers import _get_json

    local_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    candidates: list[str] = []
    seen = {local_url}

    for row in db.query(Entity).filter(Entity.status == EntityStatus.active).all():
        meta = row.metadata_ or {}
        roles = meta.get("roles") or []
        if "federation_peer" not in roles and "discovered_peer" not in roles:
            continue
        if is_peer_banned(meta):
            continue
        probe_url = (meta.get("probe_base_url") or meta.get("base_url") or "").rstrip("/")
        if not probe_url or probe_url in seen:
            continue
        seen.add(probe_url)
        try:
            manifest = _get_json(f"{probe_url}/api/v1/federation/peers/manifest", timeout=8.0)
        except Exception as exc:
            logger.debug("addr relay fetch failed %s: %s", probe_url, exc)
            continue
        for url in extract_known_peer_urls(manifest):
            if url not in seen:
                seen.add(url)
                candidates.append(url)
            if len(candidates) >= limit:
                return candidates

    return candidates[:limit]


def fetch_bootstrap_peer_urls(*, limit: int = 32) -> list[str]:
    """DNS-seed analogue — fetch peer URL list from a bootstrap JSON endpoint."""
    url = bootstrap_url()
    if not url:
        return []

    from services.federation_peers import _get_json

    try:
        payload = _get_json(url, timeout=12.0)
    except Exception as exc:
        logger.warning("bootstrap fetch failed %s: %s", url, exc)
        return []

    urls: list[str] = []
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, str) and item.strip():
                urls.append(item.strip().rstrip("/"))
            elif isinstance(item, dict):
                base = (item.get("base_url") or item.get("url") or "").strip().rstrip("/")
                if base:
                    urls.append(base)
    elif isinstance(payload, dict):
        urls.extend(extract_known_peer_urls(payload))
        for key in ("peers", "seeds", "bootstrap_peers"):
            for item in payload.get(key) or []:
                if isinstance(item, str) and item.strip():
                    urls.append(item.strip().rstrip("/"))
                elif isinstance(item, dict):
                    base = (item.get("base_url") or item.get("url") or "").strip().rstrip("/")
                    if base:
                        urls.append(base)

    seen: set[str] = set()
    out: list[str] = []
    for entry in urls:
        if entry in seen:
            continue
        seen.add(entry)
        out.append(entry)
        if len(out) >= limit:
            break
    return out


def promotion_eligible(book: dict[str, Any], *, ledger_valid: bool | None) -> bool:
    if is_peer_banned({"peer_addrbook": book}):
        return False
    if book.get("promoted_trusted"):
        return False
    if int(book.get("success_count") or 0) < promote_min_successes():
        return False
    if float(book.get("score") or 0) < promote_min_score():
        return False
    if ledger_valid is False:
        return False
    if book.get("ledger_valid") is False:
        return False
    return True


def promote_peer_to_trusted(
    db: Session,
    node_id: str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """
    Promote discovered peer to trusted_nodes.yaml when eligible (v3 auto-trust).
    If POCP_TRUSTED_NODES env is set, returns pending hint unless force=False and eligible.
    """
    from schemas.federation import TrustedNode
    from services.trust_config import (
        append_trusted_node_to_yaml,
        is_node_trusted,
        trusted_nodes_source,
    )
    from services.trust_ledger import record_trust_list_if_changed

    if is_node_trusted(node_id):
        return {"status": "already_trusted", "node_id": node_id}

    entity = db.get(Entity, peer_entity_id(node_id))
    if not entity:
        raise ValueError(f"Unknown peer node_id {node_id}")

    meta = dict(entity.metadata_ or {})
    book = get_peer_addrbook(meta)
    ledger_valid = book.get("ledger_valid")

    if not force and not promotion_eligible(book, ledger_valid=ledger_valid):
        raise ValueError(
            f"Peer {node_id} not eligible: successes={book.get('success_count')} "
            f"score={book.get('score')} ledger_valid={ledger_valid}"
        )

    public_url = (meta.get("public_base_url") or meta.get("base_url") or "").rstrip("/")
    if not public_url:
        raise ValueError(f"Peer {node_id} has no public base_url")

    if trusted_nodes_source() == "env":
        book["promotion_pending"] = True
        book["promotion_reason"] = "trust_list_locked_by_env"
        book["promotion_hint"] = (
            f'Add to POCP_TRUSTED_NODES: {{"node_id":"{node_id}","base_url":"{public_url}","trust_weight":{promote_trust_weight()}}}'
        )
        apply_addrbook_to_entity(entity, book)
        db.flush()
        return {
            "status": "pending_env",
            "node_id": node_id,
            "base_url": public_url,
            "hint": book["promotion_hint"],
        }

    trusted = TrustedNode(
        node_id=node_id,
        base_url=public_url,
        public_key=meta.get("public_key"),
        trust_weight=promote_trust_weight(),
    )
    added = append_trusted_node_to_yaml(trusted)
    now = datetime.now(timezone.utc).isoformat()
    book["promoted_trusted"] = True
    book["promoted_at"] = now
    book["promotion_pending"] = False
    book.pop("promotion_reason", None)
    book.pop("promotion_hint", None)
    meta["configured"] = True
    meta["trust_weight"] = promote_trust_weight()
    apply_addrbook_to_entity(entity, book)
    entity.metadata_ = {**meta, "peer_addrbook": book}
    ledger_event = record_trust_list_if_changed(db)
    db.flush()
    return {
        "status": "promoted" if added else "already_in_yaml",
        "node_id": node_id,
        "base_url": public_url,
        "trust_weight": promote_trust_weight(),
        "trust_source": "yaml",
        "ledger_event": ledger_event,
    }


def maybe_auto_promote_peer(
    db: Session,
    entity: Entity,
    book: dict[str, Any],
    *,
    ledger_valid: bool | None,
) -> dict[str, Any] | None:
    if not auto_promote_enabled():
        return None
    meta = entity.metadata_ or {}
    node_id = meta.get("node_id")
    if not node_id:
        return None
    if not promotion_eligible(book, ledger_valid=ledger_valid):
        return None
    try:
        return promote_peer_to_trusted(db, node_id, force=False)
    except ValueError:
        return None
    except Exception as exc:
        logger.warning("auto-promote failed for %s: %s", node_id, exc)
        return None


def list_addrbook_entries(db: Session) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for row in db.query(Entity).filter(Entity.status == EntityStatus.active).all():
        meta = row.metadata_ or {}
        roles = meta.get("roles") or []
        if "discovered_peer" not in roles and "federation_peer" not in roles:
            continue
        if meta.get("node_id") == os.getenv("POCP_NODE_ID"):
            continue
        book = get_peer_addrbook(meta)
        entries.append(
            {
                "entity_id": row.id,
                "node_id": meta.get("node_id"),
                "base_url": meta.get("public_base_url") or meta.get("base_url"),
                "probe_base_url": meta.get("probe_base_url"),
                "discovered": "discovered_peer" in roles,
                "configured": bool(meta.get("configured")),
                "peer_addrbook": book,
                "banned": is_peer_banned(meta),
                "routable": is_peer_routable(meta),
                "promotion_eligible": promotion_eligible(book, ledger_valid=book.get("ledger_valid")),
                "promoted_trusted": bool(book.get("promoted_trusted")),
            }
        )
    entries.sort(key=lambda e: (-float((e.get("peer_addrbook") or {}).get("score") or 0), e.get("node_id") or ""))
    return entries


def probe_entity_peer(db: Session, node_id: str) -> dict[str, Any]:
    """Probe a known peer and update addrbook."""
    entity = db.get(Entity, peer_entity_id(node_id))
    if not entity:
        raise ValueError(f"Unknown peer node_id {node_id}")

    meta = entity.metadata_ or {}
    probe_url = (meta.get("probe_base_url") or meta.get("base_url") or "").rstrip("/")
    if not probe_url:
        raise ValueError(f"Peer {node_id} has no probe URL")

    import time

    started = time.perf_counter()
    probe = probe_peer(probe_url)
    latency_ms = (time.perf_counter() - started) * 1000.0

    if probe.get("reachable"):
        book = record_probe_result(
            meta,
            success=True,
            latency_ms=latency_ms,
            ledger_valid=probe.get("ledger_valid"),
        )
    else:
        book = record_probe_result(meta, success=False, error=probe.get("error"), latency_ms=latency_ms)

    apply_addrbook_to_entity(entity, book)
    promotion = None
    if probe.get("reachable"):
        promotion = maybe_auto_promote_peer(
            db,
            entity,
            get_peer_addrbook(entity.metadata_ or {}),
            ledger_valid=probe.get("ledger_valid"),
        )
    db.flush()
    return {
        "node_id": node_id,
        "probe_url": probe_url,
        "reachable": bool(probe.get("reachable")),
        "peer_addrbook": get_peer_addrbook(entity.metadata_ or {}),
        "promotion": promotion,
        "probe": probe,
    }


def maintain_discovered_peers(db: Session) -> dict[str, Any]:
    """Re-probe all discovered peers (Bitcoin-style connection pool maintenance)."""
    probed = 0
    ok = 0
    failed = 0
    banned = 0
    promoted = 0
    details: list[dict[str, Any]] = []

    for row in db.query(Entity).filter(Entity.status == EntityStatus.active).all():
        meta = row.metadata_ or {}
        if "discovered_peer" not in (meta.get("roles") or []):
            continue
        node_id = meta.get("node_id")
        if not node_id:
            continue
        try:
            result = probe_entity_peer(db, node_id)
            probed += 1
            if result.get("reachable"):
                ok += 1
            else:
                failed += 1
            if is_peer_banned(result.get("peer_addrbook")):
                banned += 1
            prom = result.get("promotion") or {}
            if prom.get("status") in ("promoted", "already_in_yaml"):
                promoted += 1
            details.append(
                {
                    "node_id": node_id,
                    "reachable": result.get("reachable"),
                    "score": (result.get("peer_addrbook") or {}).get("score"),
                    "banned": is_peer_banned(result.get("peer_addrbook")),
                    "promotion": prom.get("status"),
                }
            )
        except Exception as exc:
            failed += 1
            details.append({"node_id": node_id, "error": str(exc)})

    return {
        "schema": "pocp.federation_peer_maintenance.v0.1",
        "probed": probed,
        "ok": ok,
        "failed": failed,
        "banned": banned,
        "promoted": promoted,
        "peers": details[:30],
    }
