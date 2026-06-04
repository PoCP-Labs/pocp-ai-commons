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
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
DEFAULT_BASE = "http://127.0.0.1:8008"


def get_json(url: str, timeout: float = 15) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


FEDERATION_PEER_MANIFEST_SCHEMA = "pocp.federation_peer_manifest.v0.1"
PUBLIC_SKILL_NODE_TEMPLATE_SCHEMA = "pocp-skill-node-template.v0.1"
ONTOLOGY_TYPE_COUNT = 14
REGISTRY_MIN_COUNT = 11
INFRASTRUCTURE_ENTITY_IDS = (
    "pocp-entity-local-compute",
    "pocp-entity-local-verifier",
    "pocp-entity-bob-reviewer",
    "pocp-entity-rain-sponsor",
    "pocp-entity-protocol-treasury",
    "pocp-entity-study-workflow",
)


def run_script(
    name: str,
    base: str,
    extra_args: list[str] | None = None,
    *,
    timeout: float = 180,
) -> tuple[bool, str]:
    path = SCRIPTS / name
    cmd = [sys.executable, str(path), base, *(extra_args or [])]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, out.strip()


def sync_backend_url_env(base: str) -> None:
    """Align Nexus platform_health probe with the acceptance target (avoids api: timed out)."""
    os.environ["BACKEND_URL"] = base.rstrip("/")


def _health_connect_hint(base: str) -> str:
    """Actionable hint when /health fails (Nexus super-loop often reports api: timed out)."""
    if base.rstrip("/").endswith(":8000"):
        return (
            " Hint: docker-compose.yml exposes the API on host port 8008 "
            "(try http://127.0.0.1:8008 or BACKEND_URL=http://localhost:8008)."
        )
    return ""


def step_health(base: str) -> tuple[bool, str]:
    try:
        data = get_json(f"{base.rstrip('/')}/health")
        ok = data.get("status") == "ok"
        return ok, json.dumps(data)
    except Exception as exc:
        return False, str(exc) + _health_connect_hint(base)


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


def step_federation_peer_manifest(base: str, peer: str) -> tuple[bool, str]:
    """CI-5 — local + peer federation discovery manifests and skill node template."""
    try:
        local = get_json(f"{base.rstrip('/')}/api/v1/federation/peers/manifest")
        remote = get_json(f"{peer.rstrip('/')}/api/v1/federation/peers/manifest")
        template = get_json(f"{base.rstrip('/')}/api/v1/federation/skill-node-template")
        ok = (
            local.get("schema") == FEDERATION_PEER_MANIFEST_SCHEMA
            and remote.get("schema") == FEDERATION_PEER_MANIFEST_SCHEMA
            and template.get("schema") == PUBLIC_SKILL_NODE_TEMPLATE_SCHEMA
            and bool(local.get("handshake"))
            and bool(remote.get("handshake"))
            and local.get("node_id")
            and remote.get("node_id")
            and local.get("node_id") != remote.get("node_id")
        )
        return ok, json.dumps(
            {
                "local_node_id": local.get("node_id"),
                "remote_node_id": remote.get("node_id"),
                "template_schema": template.get("schema"),
            }
        )
    except Exception as exc:
        return False, str(exc)


def step_federation_peer_handshake(base: str, peer: str) -> tuple[bool, str]:
    """CI-5 / MLN step 3–4 — capability discover + trust handshake surface.

    Runs from the acceptance runner (host URLs). Node-side POST /peers/handshake
    requires peer_base_url reachable from the API container (use docker service
    names in POCP_TRUSTED_NODES); host-side checks avoid Connection refused in
    federation compose where localhost:8101 is not visible inside node-a.
    """
    try:
        local = get_json(f"{base.rstrip('/')}/api/v1/federation/peers/manifest")
        remote = get_json(f"{peer.rstrip('/')}/api/v1/federation/peers/manifest")
        local_fp = local.get("trust_policy_bundle_fingerprint")
        remote_fp = remote.get("trust_policy_bundle_fingerprint")
        remote_handshake = remote.get("handshake") or {}
        algorithms = remote_handshake.get("algorithms") or []
        handshake_ok = bool(remote_handshake.get("handshake_version")) and bool(algorithms)

        discover_url = (
            (remote.get("discovery") or {}).get("capability_search")
            or f"{peer.rstrip('/')}/api/v1/registry/capabilities"
        )
        cap_params = "?limit=10"
        cap_path = discover_url if "?" in discover_url else f"{discover_url.rstrip('/')}{cap_params}"
        registry = get_json(cap_path)
        items = registry.get("capabilities") or registry.get("items") or []
        if isinstance(registry, list):
            items = registry

        ok = (
            handshake_ok
            and local.get("node_id")
            and remote.get("node_id")
            and local.get("node_id") != remote.get("node_id")
        )
        return ok, json.dumps(
            {
                "local_node_id": local.get("node_id"),
                "remote_node_id": remote.get("node_id"),
                "trust_bundle_aligned": bool(local_fp and remote_fp and local_fp == remote_fp),
                "discovery_count": len(items),
                "handshake_version": remote_handshake.get("handshake_version"),
            }
        )
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}: {exc.read().decode()[:200]}"
    except Exception as exc:
        return False, str(exc)


def step_entity_catalog_complete(base: str) -> tuple[bool, str]:
    """PA-5 — ontology types represented and capability registry seeded (HTTP audit)."""
    try:
        ontology = get_json(f"{base.rstrip('/')}/api/v1/entities/ontology")
        entity_types = ontology.get("entity_types") or []
        if len(entity_types) != ONTOLOGY_TYPE_COUNT:
            return False, (
                f"ontology entity_types={len(entity_types)} expected={ONTOLOGY_TYPE_COUNT}"
            )

        entities = get_json(f"{base.rstrip('/')}/api/v1/entities")
        if isinstance(entities, dict):
            items = entities.get("items") or entities.get("entities") or []
        else:
            items = entities
        by_type = Counter(e.get("entity_type") for e in items if e.get("entity_type"))
        missing_types = [t for t in entity_types if by_type.get(t, 0) == 0]

        registry = get_json(f"{base.rstrip('/')}/api/v1/registry/capabilities?limit=200")
        cap_items = registry.get("items") or []
        cap_count = registry.get("count", len(cap_items))

        entity_ids = {e.get("id") for e in items if e.get("id")}
        missing_infra = [eid for eid in INFRASTRUCTURE_ENTITY_IDS if eid not in entity_ids]

        ok = (
            not missing_types
            and cap_count >= REGISTRY_MIN_COUNT
            and not missing_infra
        )
        return ok, json.dumps(
            {
                "ontology_types": len(entity_types),
                "entity_count": len(items),
                "missing_types": missing_types,
                "capability_count": cap_count,
                "missing_infrastructure_ids": missing_infra,
            }
        )
    except Exception as exc:
        return False, str(exc)


def step_invocation_ref_integrity(base: str) -> tuple[bool, str]:
    """Smoke: dev-login → chat → exchange integrity endpoint."""
    payload = json.dumps({"username": "inv-ref-check", "email": "inv-ref-check@example.com"}).encode()
    login_req = urllib.request.Request(
        f"{base.rstrip('/')}/api/v1/auth/dev-login",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(login_req, timeout=15) as resp:
            login = json.loads(resp.read().decode())
        token = login["access_token"]
        chat_payload = json.dumps({"message": "invocation ref integrity check", "provider": "mock"}).encode()
        chat_req = urllib.request.Request(
            f"{base.rstrip('/')}/api/v1/ai/chat",
            data=chat_payload,
            method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(chat_req, timeout=30) as resp:
            chat = json.loads(resp.read().decode())
        exchange_id = chat.get("exchange_id")
        if not exchange_id:
            return False, "chat response missing exchange_id"
        integrity = get_json(f"{base.rstrip('/')}/api/v1/exchanges/{exchange_id}/integrity")
        ok = integrity.get("valid") is True
        return ok, json.dumps(
            {
                "exchange_id": exchange_id,
                "valid": integrity.get("valid"),
                "digest": integrity.get("invocation_chain_digest"),
            }
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
    sync_backend_url_env(base)
    federation = args.federation is not None
    node_b = (args.federation or "http://127.0.0.1:8101").rstrip("/")

    print(f"Phase A acceptance @ {base}" + (f" (federation, peer={node_b})" if federation else "") + (" [staging]" if args.staging else ""))
    failures: list[str] = []

    checks: list[tuple[str, callable]] = [
        ("health", lambda: step_health(base)),
        ("entity_catalog_complete", lambda: step_entity_catalog_complete(base)),
        ("intelligence/status", lambda: step_intelligence_status(base)),
        ("wallet_audit", lambda: step_wallet_audit(base)),
        ("invocation_ref_integrity", lambda: step_invocation_ref_integrity(base)),
    ]

    if args.staging:
        checks = [c for c in checks if c[0] != "invocation_ref_integrity"]
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
                (
                    "federation_peer_manifest",
                    lambda: step_federation_peer_manifest(base, node_b),
                ),
                (
                    "federation_peer_handshake",
                    lambda: step_federation_peer_handshake(base, node_b),
                ),
                ("federation_preflight", lambda: run_script("federation_pilot_preflight.py", base, [node_b])),
                ("federation_strict_mode", lambda: run_script("federation_strict_mode_test.py", base, [node_b])),
                (
                    "federation_demo",
                    lambda: run_script(
                        "federation_demo_test.py",
                        base,
                        [node_b],
                        timeout=360,
                    ),
                ),
                ("federation_exchange_demo", lambda: run_script("federation_exchange_demo_test.py", base, [node_b])),
                (
                    "cross_node_exchange_acceptance",
                    lambda: run_script(
                        "../scripts/cross_node_exchange_acceptance.py",
                        base,
                        [node_b],
                        timeout=240,
                    ),
                ),
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
            "entity_catalog_complete",
            "intelligence/status",
            "dev_login_disabled",
            "github_oauth",
            "ledger_verify",
            "wallet_audit",
            "invocation_ref_integrity",
            "crypto_readiness",
            "crypto_readiness_peer",
            "federation_peer_manifest",
            "federation_peer_handshake",
            "smoke_test",
            "federation_preflight",
            "federation_strict_mode",
            "federation_demo",
            "federation_exchange_demo",
            "cross_node_exchange_acceptance",
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
