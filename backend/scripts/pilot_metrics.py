"""Entity Network Pilot metrics — protocol, distributed intelligence, distributed compute.

Usage:
  python scripts/pilot_metrics.py http://127.0.0.1:8000
  python scripts/pilot_metrics.py --db
  python scripts/pilot_metrics.py http://127.0.0.1:8000 --json
  python scripts/pilot_metrics.py http://127.0.0.1:8000 --strict

See docs/PILOT-LAUNCH-CHECKLIST.md and docs/INTELLECTUAL-EQUALITY.md.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Pilot targets — docs/PILOT-LAUNCH-CHECKLIST.md Phase 3
PILOT_TARGETS = {
    "active_entities_min": 30,
    "active_entity_types_min": 4,
    "approved_contributions_min": 50,
    "proof_ready_min": 50,
    "invocation_traces_min": 30,
    "invocation_depth_avg_min": 3.0,
    "witness_providers_min": 2,
    "federation_imports_min": 1,
    "finalizer_entities_min": 3,
    "entity_types_with_bc_min": 2,
}


def _http_get(base: str, path: str) -> Any:
    request = urllib.request.Request(f"{base.rstrip('/')}{path}", method="GET")
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode())


def _http_get_optional(base: str, path: str) -> Any | None:
    try:
        return _http_get(base, path)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    except urllib.error.URLError:
        return None


def _verification_providers_from_status(intelligence_status: dict | None) -> list[str]:
    if not intelligence_status:
        return []
    for module in intelligence_status.get("modules") or []:
        if module.get("module") != "contribution_verification":
            continue
        providers = module.get("providers") or []
        return sorted({p for p in providers if p})
    return []


def _witness_providers_from_contributions(contributions: list[dict]) -> list[str]:
    providers: set[str] = set()
    for contrib in contributions:
        for row in contrib.get("ai_verifications") or []:
            provider = row.get("model_provider")
            if provider:
                providers.add(provider)
    return sorted(providers)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _invocation_chain_depth(trace: dict) -> int:
    steps = trace.get("steps") or []
    if not steps:
        return 1 if trace.get("initiator_id") else 0
    entities: set[str] = set()
    if trace.get("initiator_id"):
        entities.add(trace["initiator_id"])
    for step in steps:
        if step.get("source_entity_id"):
            entities.add(step["source_entity_id"])
        if step.get("target_entity_id"):
            entities.add(step["target_entity_id"])
    return max(len(entities), len(steps) + 1, 1)


def _collect_from_api(base: str, *, days: int) -> dict[str, Any]:
    health = _http_get(base, "/health")
    entities = _http_get(base, "/api/v1/entities")
    contributions = _http_get(base, "/api/v1/contributions")
    invocations = _http_get(base, "/api/v1/invocations")

    compute_status: dict | None = None
    compute_peers: dict | list | None = None
    intelligence_status: dict | None = None
    ledger_verify: dict | None = None
    federation_imports: list | None = None

    compute_status = _http_get_optional(base, "/api/v1/intelligence/compute/status")
    compute_peers = _http_get_optional(base, "/api/v1/intelligence/compute/peers")
    intelligence_status = _http_get_optional(base, "/api/v1/intelligence/status")
    ledger_verify = _http_get_optional(base, "/api/v1/ledger/verify")
    federation_imports = _http_get_optional(base, "/api/v1/federation/imports")

    return _build_metrics(
        source=f"api:{base}",
        days=days,
        health=health,
        entities=entities,
        contributions=contributions,
        invocations=invocations,
        compute_status=compute_status,
        compute_peers=compute_peers,
        intelligence_status=intelligence_status,
        ledger_verify=ledger_verify,
        federation_imports=federation_imports,
    )


def _collect_from_db(*, days: int) -> dict[str, Any]:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.orm import joinedload

    from database import SessionLocal
    from models.contribution import ContributionEvent, ContributionParticipant, ContributionStatus
    from models.entity import Entity
    from models.federation import FederatedImport
    from models.invocation import InvocationTrace
    from services.compute_registry import compute_status_manifest

    db = SessionLocal()
    try:
        entities = [
            {
                "id": e.id,
                "entity_type": e.entity_type.value,
                "name": e.name,
                "status": e.status.value,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in db.query(Entity).all()
        ]
        contributions = []
        for c in (
            db.query(ContributionEvent)
            .options(
                joinedload(ContributionEvent.participants),
                joinedload(ContributionEvent.human_reviews),
                joinedload(ContributionEvent.ai_verifications),
            )
            .all()
        ):
            contributions.append(
                {
                    "id": c.id,
                    "status": c.status.value,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "primary_entity_id": c.primary_entity_id,
                    "participants": [
                        {
                            "entity_id": p.entity_id,
                            "role": p.role.value if hasattr(p.role, "value") else str(p.role),
                        }
                        for p in c.participants
                    ],
                    "human_reviews": [
                        {
                            "reviewer_id": r.reviewer_id,
                            "approved": r.approved,
                        }
                        for r in c.human_reviews
                    ],
                    "ai_verifications": [
                        {"model_provider": v.model_provider} for v in c.ai_verifications
                    ],
                }
            )
        invocations = []
        for t in (
            db.query(InvocationTrace)
            .options(joinedload(InvocationTrace.steps))
            .order_by(InvocationTrace.created_at.desc())
            .all()
        ):
            invocations.append(
                {
                    "id": t.id,
                    "initiator_id": t.initiator_id,
                    "contribution_id": t.contribution_id,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "steps": [
                        {
                            "step_order": s.step_order,
                            "source_entity_id": s.source_entity_id,
                            "target_entity_id": s.target_entity_id,
                            "action": s.action,
                        }
                        for s in t.steps
                    ],
                }
            )
        federation_imports = [
            {
                "id": row.id,
                "source_node_id": row.source_node_id,
                "imported_at": row.imported_at.isoformat() if row.imported_at else None,
            }
            for row in db.query(FederatedImport).all()
        ]
        compute_status = compute_status_manifest()
    except SQLAlchemyError as exc:
        raise SystemExit(
            f"ERROR: database query failed — {exc}\n"
            "Ensure DATABASE_URL is set and migrations have run, or use the HTTP mode:\n"
            "  python scripts/pilot_metrics.py http://127.0.0.1:8000"
        ) from exc
    finally:
        db.close()

    return _build_metrics(
        source="database",
        days=days,
        health={"status": "ok", "service": "pocp-ai-commons", "database": "direct"},
        entities=entities,
        contributions=contributions,
        invocations=invocations,
        compute_status=compute_status,
        compute_peers=(compute_status or {}).get("peer_compute"),
        intelligence_status=None,
        ledger_verify=None,
        federation_imports=federation_imports,
    )


def _build_metrics(
    *,
    source: str,
    days: int,
    health: dict,
    entities: list[dict],
    contributions: list[dict],
    invocations: list[dict],
    compute_status: dict | None,
    compute_peers: dict | list | None,
    intelligence_status: dict | None,
    ledger_verify: dict | None,
    federation_imports: list | dict | None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=days)

    entity_by_id = {e["id"]: e for e in entities}
    entity_type_counts = Counter(e.get("entity_type") for e in entities)

    def in_window(created_at: str | None) -> bool:
        dt = _parse_dt(created_at)
        return dt is not None and dt >= window_start

    status_counts = Counter(c.get("status") for c in contributions)
    approved = [c for c in contributions if c.get("status") == "approved"]
    submitted_like = [
        c for c in contributions if c.get("status") in ("submitted", "ai_verified", "approved")
    ]

    active_entity_ids: set[str] = set()
    finalizer_ids: set[str] = set()
    entity_types_with_bc: set[str] = set()
    types_per_contribution: list[int] = []

    for contrib in contributions:
        if not in_window(contrib.get("created_at")):
            continue
        if contrib.get("status") not in ("submitted", "ai_verified", "approved", "rejected"):
            continue
        participant_ids = {p.get("entity_id") for p in contrib.get("participants") or []}
        participant_ids.add(contrib.get("primary_entity_id"))
        participant_ids.discard(None)
        active_entity_ids.update(participant_ids)
        types_in_event = {
            entity_by_id[eid]["entity_type"]
            for eid in participant_ids
            if eid in entity_by_id
        }
        if types_in_event:
            types_per_contribution.append(len(types_in_event))
        for review in contrib.get("human_reviews") or []:
            if review.get("approved") and review.get("reviewer_id"):
                finalizer_ids.add(review["reviewer_id"])
        fin = contrib.get("finalization") or {}
        if fin.get("finalizer_entity_id"):
            finalizer_ids.add(fin["finalizer_entity_id"])
        for credit in (contrib.get("rewards") or {}).get("credits") or []:
            if credit.get("ai_credits") and credit.get("entity_type"):
                entity_types_with_bc.add(credit["entity_type"])

    for trace in invocations:
        if in_window(trace.get("created_at")):
            active_entity_ids.add(trace.get("initiator_id"))
            for step in trace.get("steps") or []:
                active_entity_ids.discard(None)
                if step.get("source_entity_id"):
                    active_entity_ids.add(step["source_entity_id"])
                if step.get("target_entity_id"):
                    active_entity_ids.add(step["target_entity_id"])

    active_entity_ids.discard(None)
    active_type_counts = Counter(
        entity_by_id[eid]["entity_type"]
        for eid in active_entity_ids
        if eid in entity_by_id
    )

    depths = [_invocation_chain_depth(t) for t in invocations]
    avg_depth = round(sum(depths) / len(depths), 2) if depths else 0.0

    witness_local = list((compute_status or {}).get("active_adapters") or [])
    registered_witnesses = _verification_providers_from_status(intelligence_status)
    historical_witnesses = _witness_providers_from_contributions(contributions)
    witness_peer = 0
    if isinstance(compute_peers, dict):
        peers = compute_peers.get("peers") or compute_peers.get("items") or []
        witness_peer = sum(1 for p in peers if p.get("reachable") or p.get("status") == "ok")
    elif isinstance(compute_peers, list):
        witness_peer = sum(1 for p in compute_peers if p.get("reachable") or p.get("status") == "ok")

    peer_cfg = (compute_status or {}).get("peer_compute") or {}
    if isinstance(peer_cfg, dict) and peer_cfg.get("enabled"):
        witness_peer = max(witness_peer, peer_cfg.get("reachable_peer_count", 0) or 0)

    witness_providers = max(
        len(witness_local) + witness_peer,
        len(registered_witnesses),
        len(historical_witnesses),
    )
    import_count = len(federation_imports) if isinstance(federation_imports, list) else 0

    approval_denom = status_counts.get("submitted", 0) + status_counts.get("ai_verified", 0) + status_counts.get(
        "approved", 0
    )
    approval_rate = round(status_counts.get("approved", 0) / approval_denom, 3) if approval_denom else 0.0

    avg_types = (
        round(sum(types_per_contribution) / len(types_per_contribution), 2)
        if types_per_contribution
        else 0.0
    )

    protocol_layer = {
        "active_entities": len(active_entity_ids),
        "active_entity_types": len(active_type_counts),
        "active_entity_type_breakdown": dict(sorted(active_type_counts.items())),
        "total_entities": len(entities),
        "total_entity_type_breakdown": dict(sorted(entity_type_counts.items())),
        "approved_contributions": len(approved),
        "contribution_status_breakdown": dict(sorted(status_counts.items())),
        "proof_ready_count": len(approved),
        "avg_entity_types_per_contribution": avg_types,
        "federation_imports": import_count,
        "ledger_valid": (ledger_verify or {}).get("valid"),
        "ledger_record_count": (ledger_verify or {}).get("count"),
    }

    intelligence_layer = {
        "invocation_trace_count": len(invocations),
        "invocation_depth_avg": avg_depth,
        "invocation_depth_max": max(depths) if depths else 0,
        "finalizer_entities": len(finalizer_ids),
        "entity_types_with_bc_grants": len(entity_types_with_bc),
        "contributions_with_ai_verification": sum(
            1 for c in contributions if c.get("ai_verifications")
        ),
    }

    compute_layer = {
        "local_witness_adapters": witness_local,
        "local_witness_count": len(witness_local),
        "registered_verification_providers": registered_witnesses,
        "historical_witness_providers": historical_witnesses,
        "reachable_peer_witness_count": witness_peer,
        "witness_provider_total": witness_providers,
        "compute_node_id": (compute_status or {}).get("node_id"),
        "peer_compute_enabled": bool(
            (compute_status or {}).get("peer_compute_enabled")
            or (isinstance((compute_status or {}).get("peer_compute"), dict) and (compute_status or {}).get("peer_compute", {}).get("enabled"))
        ),
    }

    checks = {
        "active_entities": protocol_layer["active_entities"] >= PILOT_TARGETS["active_entities_min"],
        "active_entity_types": protocol_layer["active_entity_types"] >= PILOT_TARGETS["active_entity_types_min"],
        "approved_contributions": protocol_layer["approved_contributions"] >= PILOT_TARGETS["approved_contributions_min"],
        "proof_ready": protocol_layer["proof_ready_count"] >= PILOT_TARGETS["proof_ready_min"],
        "invocation_traces": intelligence_layer["invocation_trace_count"] >= PILOT_TARGETS["invocation_traces_min"],
        "invocation_depth_avg": intelligence_layer["invocation_depth_avg"] >= PILOT_TARGETS["invocation_depth_avg_min"],
        "witness_providers": compute_layer["witness_provider_total"] >= PILOT_TARGETS["witness_providers_min"],
        "federation_imports": protocol_layer["federation_imports"] >= PILOT_TARGETS["federation_imports_min"],
        "finalizer_entities": intelligence_layer["finalizer_entities"] >= PILOT_TARGETS["finalizer_entities_min"],
        "entity_types_with_bc": intelligence_layer["entity_types_with_bc_grants"]
        >= PILOT_TARGETS["entity_types_with_bc_min"],
    }

    return {
        "generated_at": now.isoformat(),
        "source": source,
        "window_days": days,
        "service": health.get("service"),
        "api_version": health.get("version"),
        "node_mode": health.get("node_mode"),
        "read_only_mirror": health.get("read_only_mirror"),
        "protocol_layer": protocol_layer,
        "distributed_intelligence_layer": intelligence_layer,
        "distributed_compute_layer": compute_layer,
        "derived": {
            "approval_rate": approval_rate,
        },
        "pilot_targets": PILOT_TARGETS,
        "pilot_checks": checks,
        "pilot_ready": all(checks.values()),
    }


def _print_human(report: dict) -> None:
    print(f"PoCP Entity Network Pilot Metrics")
    print(f"  source: {report['source']}  window: {report['window_days']}d  at: {report['generated_at']}")
    if report.get("api_version"):
        print(f"  api: v{report['api_version']}")
    print()

    p = report["protocol_layer"]
    print("=== Protocol layer ===")
    print(f"  active entities:     {p['active_entities']} / {PILOT_TARGETS['active_entities_min']}  ({p['active_entity_types']} types)")
    print(f"    types: {p['active_entity_type_breakdown']}")
    print(f"  total entities:      {p['total_entities']}  {p['total_entity_type_breakdown']}")
    print(f"  approved events:     {p['approved_contributions']} / {PILOT_TARGETS['approved_contributions_min']}")
    print(f"  proof-ready:         {p['proof_ready_count']} / {PILOT_TARGETS['proof_ready_min']}")
    print(f"  avg types/event:     {p['avg_entity_types_per_contribution']}")
    print(f"  federation imports:  {p['federation_imports']} / {PILOT_TARGETS['federation_imports_min']}")
    if p["federation_imports"] < PILOT_TARGETS["federation_imports_min"]:
        node_mode = report.get("node_mode")
        if node_mode == "full":
            print("    hint: federation imports accrue on mirror/importing nodes (Epic D Node B)")
    if p.get("ledger_valid") is not None:
        print(f"  ledger valid:        {p['ledger_valid']}  records={p.get('ledger_record_count')}")
    print()

    i = report["distributed_intelligence_layer"]
    print("=== Distributed intelligence layer ===")
    print(f"  invocation traces:   {i['invocation_trace_count']} / {PILOT_TARGETS['invocation_traces_min']}")
    print(f"  chain depth avg:     {i['invocation_depth_avg']} / {PILOT_TARGETS['invocation_depth_avg_min']}")
    print(f"  finalizer entities:  {i['finalizer_entities']} / {PILOT_TARGETS['finalizer_entities_min']}")
    print(f"  BC grant types:      {i['entity_types_with_bc_grants']} / {PILOT_TARGETS['entity_types_with_bc_min']}")
    print(f"  with AI verification:{i['contributions_with_ai_verification']}")
    print()

    c = report["distributed_compute_layer"]
    print("=== Distributed compute layer ===")
    print(f"  local witnesses:     {c['local_witness_adapters']} ({c['local_witness_count']})")
    if c.get("registered_verification_providers"):
        print(f"  registered providers:{c['registered_verification_providers']}")
    if c.get("historical_witness_providers"):
        print(f"  used in events:      {c['historical_witness_providers']}")
    print(f"  peer witnesses:      {c['reachable_peer_witness_count']}")
    print(f"  witness total:       {c['witness_provider_total']} / {PILOT_TARGETS['witness_providers_min']}")
    print(f"  peer compute:        {'on' if c['peer_compute_enabled'] else 'off'}")
    print()

    checks = report["pilot_checks"]
    passed = sum(1 for v in checks.values() if v)
    print(f"=== Pilot readiness: {passed}/{len(checks)} checks passed ===")
    for name, ok in checks.items():
        mark = "OK" if ok else "--"
        print(f"  [{mark}] {name}")
    print()
    if report["pilot_ready"]:
        print("Entity Network Pilot targets: MET")
    else:
        print("Entity Network Pilot targets: not yet met (expected during Genesis / Sprint Alpha)")


def main() -> None:
    parser = argparse.ArgumentParser(description="PoCP Entity Network Pilot metrics")
    parser.add_argument(
        "base_url",
        nargs="?",
        default=None,
        help="API base URL (default http://127.0.0.1:8000 if not using --db)",
    )
    parser.add_argument(
        "--api",
        dest="api_url",
        default=None,
        help="API base URL (alias for positional base_url; matches seed_pilot_tasks.py)",
    )
    parser.add_argument("--db", action="store_true", help="Read metrics directly from DATABASE_URL")
    parser.add_argument("--days", type=int, default=30, help="Active-entity window in days (default 30)")
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    parser.add_argument("--strict", action="store_true", help="Exit 1 unless all pilot targets are met")
    args = parser.parse_args()

    try:
        if args.db:
            report = _collect_from_db(days=args.days)
        else:
            base = args.api_url or args.base_url or "http://127.0.0.1:8000"
            if args.api_url and args.base_url and args.api_url != args.base_url:
                print("ERROR: pass API URL once — positional or --api, not both", file=sys.stderr)
                sys.exit(2)
            report = _collect_from_api(base, days=args.days)
    except urllib.error.URLError as exc:
        print(f"ERROR: cannot reach API — {exc}", file=sys.stderr)
        print("Start the API or use: python scripts/pilot_metrics.py --db", file=sys.stderr)
        sys.exit(2)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        _print_human(report)

    if args.strict and not report["pilot_ready"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
