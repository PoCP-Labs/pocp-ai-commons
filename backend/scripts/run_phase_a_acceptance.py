#!/usr/bin/env python3
"""Phase A acceptance — orchestrate Sprint Alpha + federation E2E scripts.

Usage:
  python backend/scripts/run_phase_a_acceptance.py [base_url]
  python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101
  python backend/scripts/run_phase_a_acceptance.py https://api.staging.example --staging --skip-optional

Exit 0 when all required steps pass; 1 on failure.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
DEFAULT_BASE = "http://127.0.0.1:8000"


def get_json(url: str, timeout: float = 15) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def run_script(name: str, base: str, extra_args: list[str] | None = None) -> tuple[bool, str]:
    path = SCRIPTS / name
    cmd = [sys.executable, str(path), base, *(extra_args or [])]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, out.strip()


def step_health(base: str) -> tuple[bool, str]:
    try:
        data = get_json(f"{base.rstrip('/')}/health")
        ok = data.get("status") == "ok"
        return ok, json.dumps(data)
    except Exception as exc:
        return False, str(exc)


def step_crypto_readiness(base: str, *, require_hybrid: bool = False) -> tuple[bool, str]:
    try:
        data = get_json(f"{base.rstrip('/')}/api/v1/crypto/readiness")
        if require_hybrid:
            ok = (
                data.get("active_crypto_suite") == "pocp-crypto-v0.2-hybrid"
                and data.get("hybrid_signing_enabled") is True
            )
        else:
            ok = bool(data.get("active_crypto_suite"))
        return ok, json.dumps(
            {
                "suite": data.get("active_crypto_suite"),
                "hybrid": data.get("hybrid_signing_enabled"),
                "hash": data.get("active_hash_algorithm"),
            }
        )
    except Exception as exc:
        return False, str(exc)


def step_intelligence_status(base: str) -> tuple[bool, str]:
    try:
        data = get_json(f"{base.rstrip('/')}/api/v1/intelligence/status")
        modules = data.get("modules") or []
        return len(modules) >= 5, f"modules={len(modules)} active={data.get('modules_active')}"
    except Exception as exc:
        return False, str(exc)


def step_dev_login_disabled(base: str) -> tuple[bool, str]:
    payload = json.dumps({"username": "staging-check", "email": "staging-check@example.com"}).encode()
    request = urllib.request.Request(
        f"{base.rstrip('/')}/api/v1/auth/dev-login",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15):
            return False, "dev-login should return 403 when disabled"
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            return True, "dev-login disabled"
        return False, f"HTTP {exc.code}: {exc.read().decode()[:120]}"
    except Exception as exc:
        return False, str(exc)


def step_github_oauth_ready(base: str) -> tuple[bool, str]:
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(f"{base.rstrip('/')}/api/v1/auth/github/login", method="GET")
    try:
        opener.open(request, timeout=15)
        return False, "expected redirect to GitHub OAuth"
    except urllib.error.HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308):
            location = exc.headers.get("Location", "")
            if "github.com" in location and "client_id=" in location:
                return True, "github oauth redirect configured"
            return False, f"unexpected redirect: {location[:120]}"
        body = exc.read().decode()[:120]
        return False, f"HTTP {exc.code}: {body}"
    except Exception as exc:
        return False, str(exc)


def step_ledger_verify(base: str) -> tuple[bool, str]:
    try:
        data = get_json(f"{base.rstrip('/')}/api/v1/ledger/verify")
        ok = data.get("valid") is True
        return ok, f"valid={data.get('valid')} count={data.get('count')}"
    except Exception as exc:
        return False, str(exc)


def step_wallet_audit(base: str) -> tuple[bool, str]:
    try:
        data = get_json(f"{base.rstrip('/')}/api/v1/wallets/audit")
        ok = data.get("valid") is True
        return ok, (
            f"valid={data.get('valid')} wallets={data.get('wallet_count')} "
            f"invalid={data.get('invalid_count')}"
        )
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase A acceptance runner")
    parser.add_argument("base", nargs="?", default=DEFAULT_BASE, help="API base URL")
    parser.add_argument(
        "--federation",
        metavar="NODE_B_URL",
        default=None,
        help="If set, run federation E2E against node A (base) and optional node B URL",
    )
    parser.add_argument("--skip-optional", action="store_true", help="Skip optional demo scripts")
    parser.add_argument(
        "--staging",
        action="store_true",
        help="Public staging mode: no dev-login smoke; require OAuth config and dev-login disabled",
    )
    args = parser.parse_args()

    base = args.base.rstrip("/")
    federation = args.federation is not None
    node_b = (args.federation or "http://127.0.0.1:8101").rstrip("/")

    print(f"Phase A acceptance @ {base}" + (f" (federation, peer={node_b})" if federation else "") + (" [staging]" if args.staging else ""))
    failures: list[str] = []

    checks: list[tuple[str, callable]] = [
        ("health", lambda: step_health(base)),
        ("intelligence/status", lambda: step_intelligence_status(base)),
        ("wallet_audit", lambda: step_wallet_audit(base)),
    ]

    if args.staging:
        checks.extend(
            [
                ("dev_login_disabled", lambda: step_dev_login_disabled(base)),
                ("github_oauth", lambda: step_github_oauth_ready(base)),
                ("crypto_readiness", lambda: step_crypto_readiness(base)),
                ("ledger_verify", lambda: step_ledger_verify(base)),
            ]
        )
    else:
        checks.append(("smoke_test", lambda: run_script("smoke_test.py", base)))

    if federation:
        checks.extend(
            [
                ("crypto_readiness", lambda: step_crypto_readiness(base)),
                ("crypto_readiness_peer", lambda: step_crypto_readiness(node_b)),
                ("federation_preflight", lambda: run_script("federation_pilot_preflight.py", base, [node_b])),
                ("federation_strict_mode", lambda: run_script("federation_strict_mode_test.py", base, [node_b])),
                ("federation_demo", lambda: run_script("federation_demo_test.py", base, [node_b])),
                ("federation_exchange_demo", lambda: run_script("federation_exchange_demo_test.py", base, [node_b])),
                ("peer_witness_verify", lambda: run_script("peer_witness_verify_test.py", base)),
                ("peer_mcp_demo", lambda: run_script("peer_mcp_demo_test.py", base)),
            ]
        )
    else:
        checks.append(("mcp_import_demo", lambda: run_script("mcp_import_demo_test.py", base)))

    if not args.skip_optional:
        checks.extend(
            [
                ("crewai_witness_demo", lambda: run_script("crewai_witness_demo_test.py", base)),
                ("crewai_witness_e2e", lambda: run_script("crewai_witness_e2e_test.py", base)),
                ("pilot_metrics", lambda: run_script("pilot_metrics.py", base)),
            ]
        )

    for name, fn in checks:
        try:
            ok, detail = fn()
        except subprocess.TimeoutExpired:
            ok, detail = False, "timeout"
        except urllib.error.URLError as exc:
            ok, detail = False, str(exc.reason)

        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {name}")
        if detail and (not ok or len(detail) < 200):
            for line in detail.splitlines()[:8]:
                print(f"         {line}")
        elif detail and not ok:
            print(f"         {detail[:400]}…")

        if not ok and name in (
            "health",
            "intelligence/status",
            "dev_login_disabled",
            "github_oauth",
            "ledger_verify",
            "wallet_audit",
            "crypto_readiness",
            "crypto_readiness_peer",
            "smoke_test",
            "federation_preflight",
            "federation_strict_mode",
            "federation_demo",
            "federation_exchange_demo",
            "peer_witness_verify",
            "peer_mcp_demo",
        ):
            failures.append(name)

    if failures:
        print(f"\nPhase A FAILED — required steps: {', '.join(failures)}")
        return 1

    print("\nPhase A PASS — demonstrable loop verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
