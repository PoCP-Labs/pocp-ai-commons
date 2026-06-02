#!/usr/bin/env python3
"""Dispatch Protocol Layer mission to Agent Studio — Issues → PA (handoffs) → optional Cursor.

Creates mission `protocol_layer_edp`, spawns Meta Agent handoffs, optionally opens GitHub
Issues (PL-1..PL-10), and runs Cursor automation tick if configured.

Usage:
  python backend/scripts/dispatch_protocol_layer_studio.py
  python backend/scripts/dispatch_protocol_layer_studio.py --create-issues --cursor-tick
  python backend/scripts/dispatch_protocol_layer_studio.py --api http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_BACKEND = _REPO / "backend"
sys.path.insert(0, str(_BACKEND))

try:
    from dotenv import load_dotenv

    load_dotenv(_BACKEND / ".env", override=False)
except ImportError:
    pass

PLAN_ID = "protocol_layer_edp"

GITHUB_ISSUES: list[dict[str, str]] = [
    {
        "title": "[Protocol PL-1] EDP v0.1 spec + ontology cross-links",
        "labels": "backend,entity,documentation",
        "body": """## Problem
Entity Dialogue Protocol v0.1 exists but must align with ENTITY-CONNECTION and TRUST-POLICY-BUNDLE.

## Scope
- Review `docs/protocol/ENTITY-DIALOGUE-PROTOCOL.md`
- Cross-link ENTITY-CONNECTION, CHAIN-AND-NODE-PLAN
- Draft v0.2 sections for `quote` and `federation_accept`

## Acceptance
- [ ] Atlas review PASS
- [ ] `pytest backend/tests/test_entity_dialogue.py -q` green

## PA
Agent Studio handoff → **Atlas-0** (plan `protocol_layer_edp`)
""",
    },
    {
        "title": "[Protocol PL-2] Dialogue invoke → metered capability_execute",
        "labels": "backend,entity",
        "body": """## Problem
`invoke` dialogue kind only records InvocationTrace steps; metered execution still bypasses via REST.

## Expected
POST dialogue `invoke` optionally runs `execute_skill` / `execute_agent` and attaches CapabilityReceipt.

## Acceptance
- [ ] invoke with `payload.execute=true` runs capability path
- [ ] pytest entity_dialogue + capability_execute green

## PA
**Pulse-0** after Atlas PL-1
""",
    },
    {
        "title": "[Protocol PL-3] quote kind + Exchange Spine binding",
        "labels": "backend,entity",
        "body": """## Problem
Exchange quote intent has no native dialogue kind.

## Expected
`quote` kind creates exchange intent; links to invoke + exchange_settled spine.

## PA
**Vault-0**
""",
    },
    {
        "title": "[Protocol PL-4] federation_accept + peer dialogue routing",
        "labels": "backend,entity",
        "body": """## Problem
Cross-node dialogue is proof-mailbox only; federation_accept not implemented.

## Expected
federation_accept validates proof via trust bundle; peer dialogue endpoint documented.

## PA
**Mesh-0**
""",
    },
    {
        "title": "[Protocol PL-5] REST/A2A → dialogue binding map",
        "labels": "backend,documentation",
        "body": """## Problem
REST and A2A routes lack explicit mapping to dialogue kinds — 拼装车 risk.

## Expected
`docs/protocol/BINDING-TO-DIALOGUE.md` with route → kind table; A2A submit deferred binding.

## PA
**Atlas-0** + **Pulse-0**
""",
    },
    {
        "title": "[Protocol PL-6] Proof packet dialogue_id refs",
        "labels": "backend,entity",
        "body": """## Problem
Proof export may omit dialogue_id from invocation step metadata.

## Expected
proof.py includes dialogue refs in invocation_trace section.

## PA
**Vault-0**
""",
    },
    {
        "title": "[Protocol PL-7] Entity Dialogue UI panel",
        "labels": "frontend,entity",
        "body": """## Problem
No UI for native dialogue envelope — developers must use curl.

## Expected
EntityDetail tab: ping / discover / invoke forms → POST .../dialogue

## PA
**Canvas-0**
""",
    },
    {
        "title": "[Protocol PL-8] Dialogue API docs in LOCAL-SETUP",
        "labels": "documentation",
        "body": """## Problem
LOCAL-SETUP and protocol README lack dialogue examples.

## PA
**Herald-0**
""",
    },
    {
        "title": "[Protocol PL-9] Protocol layer acceptance gate",
        "labels": "testing,backend",
        "body": """## Problem
Need consolidated protocol-layer test gate before v0.2 merge.

## Acceptance
pytest: entity_dialogue, entity_connections, trust_policy_bundle, protocol_layer

## PA
**Gauge-0**
""",
    },
    {
        "title": "[Protocol PL-10] Nexus consolidate protocol_layer_edp mission",
        "labels": "backend",
        "body": """## Problem
Close protocol layer mission when all PL PAs complete.

## PA
**Nexus-0** ← **Gauge-0**
""",
    },
]


def _api(base: str, method: str, path: str, body: dict | None = None) -> dict:
    url = f"{base.rstrip('/')}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _dispatch_in_process() -> dict:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from database import Base
    from services.agent_studio.mission_plans import create_mission_from_plan
    from services.agent_studio.nexus_autopilot import run_nexus_autopilot
    from services.meta_agent_registry import ensure_meta_agents

    db_url = os.getenv("DATABASE_URL", f"sqlite:///{_BACKEND / 'pocp.db'}")
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        ensure_meta_agents(db)
        result = create_mission_from_plan(db, PLAN_ID, activate=True, spawn_handoffs=True)
        mission = result["mission"]
        if mission.get("id"):
            from models.agent_studio import AgentStudioMission

            row = db.get(AgentStudioMission, mission["id"])
            if row is not None:
                row.metadata_ = {
                    **(row.metadata_ or {}),
                    "plan_id": PLAN_ID,
                    "track": "protocol_layer",
                    "issues": [f"PL-{i}" for i in range(1, 11)],
                }
                db.flush()
        nexus = run_nexus_autopilot(db)
        db.commit()
        return {"mode": "in_process", "mission": result, "nexus": nexus}
    finally:
        db.close()


def _dispatch_via_api(base: str) -> dict:
    _api(base, "POST", "/api/v1/agent-studio/ensure-agents")
    mission = _api(base, "POST", f"/api/v1/agent-studio/missions/from-plan/{PLAN_ID}")
    nexus = _api(
        base,
        "POST",
        "/api/v1/agent-studio/nexus/autopilot",
    )
    return {"mode": "api", "base": base, "mission": mission, "nexus": nexus}


def _create_github_issues(repo: str, *, dry_run: bool) -> list[dict]:
    results: list[dict] = []
    gh = subprocess.run(["gh", "--version"], capture_output=True, text=True)
    if gh.returncode != 0:
        return [{"ok": False, "error": "gh CLI not installed"}]

    for item in GITHUB_ISSUES:
        if dry_run:
            results.append({"ok": True, "dry_run": True, "title": item["title"]})
            continue
        proc = subprocess.run(
            [
                "gh",
                "issue",
                "create",
                "--repo",
                repo,
                "--title",
                item["title"],
                "--body",
                item["body"],
                "--label",
                item["labels"],
            ],
            capture_output=True,
            text=True,
        )
        results.append(
            {
                "ok": proc.returncode == 0,
                "title": item["title"],
                "url": (proc.stdout or "").strip() if proc.returncode == 0 else None,
                "error": (proc.stderr or proc.stdout or "")[:500] if proc.returncode != 0 else None,
            }
        )
    return results


def _cursor_tick(base: str | None) -> dict:
    if base:
        try:
            return _api(base, "POST", "/api/v1/agent-studio/cursor/run?max_handoffs=1")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return {"ran": False, "error": body[:500]}

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from database import Base
    from services.agent_studio.cursor_automation import run_cursor_automation_tick
    from services.meta_agent_registry import ensure_meta_agents

    db_url = os.getenv("DATABASE_URL", f"sqlite:///{_BACKEND / 'pocp.db'}")
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        ensure_meta_agents(db)
        result = run_cursor_automation_tick(db, max_handoffs=1)
        db.commit()
        return result
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch protocol layer mission to Agent Studio")
    parser.add_argument("--api", default=os.getenv("POCP_API_BASE", ""), help="API base URL (empty = in-process DB)")
    parser.add_argument("--create-issues", action="store_true", help="Create GitHub Issues PL-1..PL-10 via gh CLI")
    parser.add_argument("--issues-dry-run", action="store_true", help="List issues that would be created")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", "PoCP-Labs/pocp-ai-commons"))
    parser.add_argument("--cursor-tick", action="store_true", help="Run one Cursor automation handoff after dispatch")
    parser.add_argument("--super-tick", action="store_true", help="Run Nexus super-loop (plan + cursor + learn)")
    args = parser.parse_args()

    print(f"\n=== Protocol Layer Studio Dispatch ===\nplan_id={PLAN_ID}\n")

    if args.create_issues or args.issues_dry_run:
        print("GitHub Issues (PL-1..PL-10):")
        issue_results = _create_github_issues(args.repo, dry_run=args.issues_dry_run)
        for r in issue_results:
            status = "DRY" if r.get("dry_run") else ("OK" if r.get("ok") else "FAIL")
            print(f"  [{status}] {r.get('title') or r.get('error')}")
            if r.get("url"):
                print(f"         {r['url']}")
        print()

    try:
        if args.api.strip():
            payload = _dispatch_via_api(args.api.strip())
        else:
            payload = _dispatch_in_process()
    except Exception as exc:
        print(f"Dispatch FAILED: {exc}")
        return 1

    mission = payload.get("mission") or {}
    handoff_count = mission.get("handoff_count") or len(mission.get("handoffs") or [])
    mid = (mission.get("mission") or {}).get("id") or mission.get("id")
    print(f"Mission: {mid}")
    print(f"Handoffs spawned (PA): {handoff_count}")
    print(f"Mode: {payload.get('mode')}")

    if args.super_tick and args.api.strip():
        print("\nRunning Nexus super-tick...")
        try:
            st = _api(args.api.strip(), "POST", "/api/v1/agent-studio/nexus/super-tick?max_cursor_handoffs=1")
            print(f"  super-tick: cursor processed={len(st.get('cursor', {}).get('processed', []))}")
        except Exception as exc:
            print(f"  super-tick failed: {exc}")

    if args.cursor_tick:
        print("\nRunning Cursor automation tick (1 handoff)...")
        tick = _cursor_tick(args.api.strip() or None)
        if tick.get("ran"):
            processed = tick.get("processed") or []
            print(f"  processed: {len(processed)} handoff(s)")
            for p in processed:
                print(f"    - {p.get('handoff_id')}: {p.get('status')}")
        else:
            print(f"  skipped: {tick.get('reason') or tick.get('error') or 'automation inactive'}")
            print("  Hint: set POCP_CURSOR_AUTOMATION=true and CURSOR_API_KEY, or use Agent Studio UI.")

    print("\nNext:")
    print("  UI → Agent Studio tab → view pending handoffs")
    print(f"  API → GET /api/v1/agent-studio/cursor/pending")
    print(f"  Docs → agents/missions/protocol-layer-edp/MANIFEST.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
