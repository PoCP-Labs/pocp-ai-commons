#!/usr/bin/env python3
"""Agent Studio end-to-end smoke test (API chain, optional Cursor handoff)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))

def _req(
    base: str,
    method: str,
    path: str,
    body: dict | None = None,
    *,
    timeout: float = 120,
) -> dict | list:
    url = f"{base.rstrip('/')}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def step(name: str, fn) -> tuple[bool, str]:
    try:
        detail = fn()
        print(f"  PASS  {name}")
        if detail:
            print(f"        {detail}")
        return True, detail
    except Exception as exc:
        print(f"  FAIL  {name}: {exc}")
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=os.getenv("POCP_API_BASE", "http://127.0.0.1:8008"))
    parser.add_argument("--skip-cursor", action="store_true", help="Skip live Cursor handoff (faster)")
    parser.add_argument("--cursor-timeout", type=int, default=600)
    args = parser.parse_args()
    base = args.base

    print(f"\n=== Agent Studio E2E ===\nAPI: {base}\n")
    results: list[tuple[str, bool]] = []

    def record(name: str, ok: bool) -> None:
        results.append((name, ok))

    # 1 Health
    ok, _ = step("Health /health", lambda: _req(base, "GET", "/health").get("service"))
    record("health", ok)

    # 2 Meta agents on graph
    ok, detail = step(
        "POST /meta-agents/ensure",
        lambda: (
            lambda r: f"count={len(r) if isinstance(r, list) else r.get('count', '?')}"
        )(_req(base, "POST", "/api/v1/meta-agents/ensure")),
    )
    record("meta_agents_ensure", ok)

    # 3 Agent Studio ensure
    ok, detail = step(
        "POST /agent-studio/ensure-agents",
        lambda: f"count={_req(base, 'POST', '/api/v1/agent-studio/ensure-agents').get('count')}",
    )
    record("studio_ensure_agents", ok)

    # 4 Dashboard + cursor block
    dash_holder: dict = {}

    def load_dashboard() -> str:
        dash = _req(base, "GET", "/api/v1/agent-studio/dashboard")
        dash_holder["dash"] = dash
        ca = dash.get("cursor_automation") or {}
        stats = dash.get("stats") or {}
        return (
            f"agents={stats.get('meta_agents')} missions_active={stats.get('active_missions')} "
            f"cursor_active={ca.get('automation_active')} pending_cursor={ca.get('pending_for_cursor')}"
        )

    ok, _ = step("GET /agent-studio/dashboard", load_dashboard)
    record("dashboard", ok)

    # 5 Mission plans
    ok, detail = step(
        "GET /agent-studio/mission-plans",
        lambda: f"plans={len(_req(base, 'GET', '/api/v1/agent-studio/mission-plans'))}",
    )
    record("mission_plans", ok)

    # 6 Nexus autopilot
    nexus_holder: dict = {}

    def nexus_autopilot() -> str:
        tick = _req(base, "POST", "/api/v1/agent-studio/nexus/autopilot")
        nexus_holder["tick"] = tick
        return f"mode={tick.get('mode')} pending={tick.get('pending_handoff_count')}"

    ok, _ = step("POST /agent-studio/nexus/autopilot", nexus_autopilot)
    record("nexus_autopilot", ok)

    # 7 Nexus status
    ok, detail = step(
        "GET /agent-studio/nexus/status",
        lambda: (
            lambda s: f"mission={(s.get('active_mission') or {}).get('title', 'none')[:40]} "
            f"pending={s.get('pending_handoff_count')}"
        )(_req(base, "GET", "/api/v1/agent-studio/nexus/status")),
    )
    record("nexus_status", ok)

    # 8 Cursor status
    cursor_holder: dict = {}

    def cursor_status() -> str:
        st = _req(base, "GET", "/api/v1/agent-studio/cursor/status")
        cursor_holder["status"] = st
        return (
            f"active={st.get('automation_active')} sdk={st.get('sdk_installed')} "
            f"key={st.get('api_key_configured')} pending={st.get('pending_for_cursor')}"
        )

    ok, _ = step("GET /agent-studio/cursor/status", cursor_status)
    record("cursor_status", ok)

    # 9 Cursor run (optional live)
    if not args.skip_cursor:
        st = cursor_holder.get("status") or {}
        if not st.get("automation_active"):
            print("  SKIP  POST /agent-studio/cursor/run (automation not active)")
            record("cursor_run", False)
        elif (st.get("pending_for_cursor") or 0) < 1:
            print("  SKIP  POST /agent-studio/cursor/run (no pending handoffs)")
            record("cursor_run", True)  # idle is ok
        else:
            print(f"  RUN   POST /agent-studio/cursor/run (timeout {args.cursor_timeout}s)...")
            t0 = time.monotonic()
            try:
                tick = _req(
                    base,
                    "POST",
                    "/api/v1/agent-studio/cursor/run?max_handoffs=1",
                    timeout=args.cursor_timeout,
                )
                elapsed = int(time.monotonic() - t0)
                processed = tick.get("processed") or []
                if processed:
                    p = processed[0]
                    c = p.get("cursor") or {}
                    line = (
                        f"handoff={p.get('handoff_id', '')[:8]}… status={p.get('status')} "
                        f"cursor_ok={c.get('ok')} elapsed={elapsed}s"
                    )
                    if c.get("startup_error"):
                        line += f" err={c.get('message', '')[:80]}"
                else:
                    line = f"ran={tick.get('ran')} reason={tick.get('reason', '')} elapsed={elapsed}s"
                ok_run = bool(processed) and processed[0].get("status") == "completed"
                print(f"  {'PASS' if ok_run else 'WARN'}  cursor/run — {line}")
                record("cursor_run", ok_run)
            except Exception as exc:
                print(f"  FAIL  cursor/run: {exc}")
                record("cursor_run", False)
    else:
        print("  SKIP  cursor/run (--skip-cursor)")
        record("cursor_run", True)

    # 10 Super-loop (plan + PDCA without Cursor when max=0)
    ok, detail = step(
        "GET /agent-studio/nexus/super-loop/status",
        lambda: (
            lambda s: f"enabled={s.get('enabled')} interval={s.get('interval_sec')}"
        )(_req(base, "GET", "/api/v1/agent-studio/nexus/super-loop/status")),
    )
    record("super_loop_status", ok)

    ok, detail = step(
        "POST /agent-studio/nexus/super-tick",
        lambda: (
            lambda t: (
                f"nexus_mode={t.get('nexus', {}).get('mode')} "
                f"pending={t.get('pending_for_cursor')} healthy={t.get('platform_healthy')}"
            )
        )(
            _req(
                base,
                "POST",
                "/api/v1/agent-studio/nexus/super-tick?max_cursor_handoffs=0",
                timeout=120,
            )
        ),
    )
    record("super_tick", ok)

    # 11 Learning cycle
    ok, detail = step(
        "POST /agent-studio/nexus/learning-cycle",
        lambda: f"keys={list(_req(base, 'POST', '/api/v1/agent-studio/nexus/learning-cycle').keys())[:5]}",
    )
    record("nexus_learning", ok)

    # 12 Progress review
    ok, _ = step(
        "GET /agent-studio/nexus/progress-review",
        lambda: (
            lambda r: f"completion={r.get('completion_percent')}%"
        )(_req(base, "GET", "/api/v1/agent-studio/nexus/progress-review")),
    )
    record("progress_review", ok)

    # 13 Graph has meta agents
    ok, detail = step(
        "GET /graph (meta_agent nodes)",
        lambda: f"meta_agent_nodes={_req(base, 'GET', '/api/v1/graph').get('meta_agent_nodes', 0)}",
    )
    record("graph_meta_agents", ok)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\n=== Summary: {passed}/{total} steps OK ===\n")
    for name, ok in results:
        print(f"  {'OK' if ok else 'FAIL'}  {name}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
