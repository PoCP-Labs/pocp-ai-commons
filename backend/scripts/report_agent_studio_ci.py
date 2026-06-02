#!/usr/bin/env python3
"""Report CI pytest/acceptance results to Agent Studio (Gauge-0 + mission outcomes)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))

GAUGE_ID = "pocp-agent-gauge-0"
NEXUS_ID = "pocp-agent-nexus-0"
PIPELINE_ID = "pocp-agent-pipeline-0"


def _post(base: str, path: str, body: dict | None = None) -> dict:
    url = f"{base.rstrip('/')}{path}"
    data = json.dumps(body or {}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data if body is not None else None,
        headers={"Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(base: str, path: str) -> dict | list:
    url = f"{base.rstrip('/')}{path}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ensure_ci_mission(base: str, title: str) -> str:
    missions = _get(base, "/api/v1/agent-studio/missions")
    for m in missions:
        if m.get("title") == title and m.get("status") == "active":
            return m["id"]
    created = _post(
        base,
        "/api/v1/agent-studio/missions",
        {
            "title": title,
            "description": "Auto-created by CI reporter",
            "kind": "improve",
            "orchestrator_entity_id": NEXUS_ID,
        },
    )
    mid = created["id"]
    _post(base, f"/api/v1/agent-studio/missions/{mid}/activate")
    return mid


def record_outcome(
    base: str,
    *,
    mission_id: str | None,
    agent_entity_id: str,
    kind: str,
    result: str,
    summary: str,
    evidence: dict,
    auto_evaluate: bool = True,
) -> dict:
    return _post(
        base,
        "/api/v1/agent-studio/outcomes",
        {
            "agent_entity_id": agent_entity_id,
            "kind": kind,
            "result": result,
            "mission_id": mission_id,
            "summary": summary,
            "evidence": evidence,
            "auto_evaluate": auto_evaluate,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Report CI results to Agent Studio")
    parser.add_argument("--api", default=os.getenv("POCP_AGENT_STUDIO_API", "http://127.0.0.1:8765"))
    parser.add_argument("--pytest-exit", type=int, default=0)
    parser.add_argument("--acceptance-exit", type=int, default=0)
    parser.add_argument("--mission-title", default=None)
    parser.add_argument("--skip-api", action="store_true", help="Dry run without HTTP")
    parser.add_argument("--no-auto-evaluate", action="store_true")
    args = parser.parse_args()

    sha = os.getenv("GITHUB_SHA", "local")[:12]
    ref = os.getenv("GITHUB_REF_NAME", "local")
    title = args.mission_title or f"CI {ref} {sha}"

    evidence = {
        "source": "github_actions",
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_ref": os.getenv("GITHUB_REF_NAME"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "pytest_exit": args.pytest_exit,
        "acceptance_exit": args.acceptance_exit,
    }

    if args.skip_api:
        print(json.dumps({"dry_run": True, "title": title, "evidence": evidence}, indent=2))
        return 0

    try:
        _post(args.api, "/api/v1/agent-studio/ensure-agents")
        mission_id = ensure_ci_mission(args.api, title)

        pytest_result = "pass" if args.pytest_exit == 0 else "fail"
        acc_result = "pass" if args.acceptance_exit == 0 else "fail"

        r1 = record_outcome(
            args.api,
            mission_id=mission_id,
            agent_entity_id=GAUGE_ID,
            kind="test",
            result=pytest_result,
            summary=f"pytest exit code {args.pytest_exit}",
            evidence=evidence,
            auto_evaluate=not args.no_auto_evaluate,
        )
        r2 = record_outcome(
            args.api,
            mission_id=mission_id,
            agent_entity_id=GAUGE_ID,
            kind="acceptance",
            result=acc_result,
            summary=f"phase_a acceptance exit code {args.acceptance_exit}",
            evidence=evidence,
            auto_evaluate=not args.no_auto_evaluate,
        )
        record_outcome(
            args.api,
            mission_id=mission_id,
            agent_entity_id=PIPELINE_ID,
            kind="metric",
            result="pass" if args.pytest_exit == 0 and args.acceptance_exit == 0 else "partial",
            summary="CI pipeline completed outcome report",
            evidence=evidence,
            auto_evaluate=False,
        )

        print(json.dumps({"mission_id": mission_id, "pytest": r1, "acceptance": r2}, indent=2))
        return 0 if args.pytest_exit == 0 and args.acceptance_exit == 0 else 1
    except urllib.error.URLError as exc:
        print(f"Agent Studio API unreachable: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
