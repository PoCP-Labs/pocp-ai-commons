#!/usr/bin/env python3
"""Verify Phase A staging backend/.env before public deploy.

Usage:
  python backend/scripts/verify_staging_env.py
  python backend/scripts/verify_staging_env.py path/to/.env
  python backend/scripts/verify_staging_env.py --check-example

Exit 0 when required Phase A staging settings look ready; 1 otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path

REQUIRED = (
    "BACKEND_URL",
    "FRONTEND_URL",
    "JWT_SECRET",
    "DATABASE_URL",
    "GITHUB_CLIENT_ID",
    "GITHUB_CLIENT_SECRET",
    "GITHUB_OAUTH_CALLBACK_URL",
)

PLACEHOLDER_FRAGMENTS = (
    "CHANGE_ME",
    "replace-with",
    "your-staging-host.example",
    "example.com",
    "<",
)


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, raw = line.partition("=")
        values[key.strip()] = raw.strip().strip('"').strip("'")
    return values


def template_declares_keys(path: Path, keys: tuple[str, ...]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    missing: list[str] = []
    for key in keys:
        if f"{key}=" not in text:
            missing.append(f"template missing {key}")
    return missing


def check_example_template(root: Path) -> int:
    """CI hook: ensure .env.staging.example documents the public staging profile."""
    env_path = root / "backend" / ".env.staging.example"
    if not env_path.is_file():
        print(f"FAIL: template not found: {env_path}")
        return 1

    env = load_env(env_path)
    failures: list[str] = template_declares_keys(env_path, REQUIRED)

    dev_login = env.get("ENABLE_DEV_LOGIN", "true").strip().lower()
    if dev_login in ("true", "1", "yes", "on"):
        failures.append("ENABLE_DEV_LOGIN must be false in .env.staging.example")

    compose = root / "docker-compose.staging.yml"
    if not compose.is_file():
        failures.append("missing docker-compose.staging.yml")

    print(f"Phase A staging template check: {env_path}")
    print(f"  [{'OK' if dev_login not in ('true', '1', 'yes', 'on') else 'FAIL'}] ENABLE_DEV_LOGIN=false")
    declared = {line.split("=", 1)[0].strip() for line in env_path.read_text(encoding="utf-8").splitlines() if "=" in line and not line.strip().startswith("#")}
    for key in REQUIRED:
        print(f"  [{'OK' if key in declared else 'FAIL'}] {key}")
    print(f"  [{'OK' if compose.is_file() else 'FAIL'}] docker-compose.staging.yml")

    for f in failures:
        print(f"  [FAIL] {f}")

    if failures:
        print("\nStaging template NOT ready for CI.")
        return 1

    print("\nStaging template OK for CI (fill backend/.env before deploy).")
    return 0


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    if len(sys.argv) > 1 and sys.argv[1] in ("--check-example", "--example"):
        return check_example_template(root)

    env_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "backend" / ".env"
    if not env_path.is_file():
        print(f"FAIL: env file not found: {env_path}")
        print("Copy backend/.env.staging.example to backend/.env and fill secrets.")
        return 1

    env = load_env(env_path)
    failures: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED:
        value = env.get(key, "").strip()
        if not value:
            failures.append(f"missing {key}")
            continue
        if any(frag in value for frag in PLACEHOLDER_FRAGMENTS):
            failures.append(f"{key} still looks like a placeholder")

    dev_login = env.get("ENABLE_DEV_LOGIN", "true").strip().lower()
    if dev_login in ("true", "1", "yes", "on"):
        failures.append("ENABLE_DEV_LOGIN must be false on public staging")

    backend_url = env.get("BACKEND_URL", "").rstrip("/")
    callback = env.get("GITHUB_OAUTH_CALLBACK_URL", "")
    if backend_url and callback and not callback.startswith(backend_url):
        warnings.append("GITHUB_OAUTH_CALLBACK_URL does not share BACKEND_URL prefix")

    if env.get("APP_ENV", "").lower() not in ("staging", "production"):
        warnings.append("APP_ENV is not staging/production")

    print(f"Phase A staging env check: {env_path}")
    for key in REQUIRED:
        value = env.get(key, "").strip()
        if not value:
            mark = "FAIL"
        elif any(frag in value for frag in PLACEHOLDER_FRAGMENTS):
            mark = "FAIL"
        else:
            mark = "OK"
        print(f"  [{mark}] {key}")

    print(f"  [{'OK' if dev_login not in ('true', '1', 'yes', 'on') else 'FAIL'}] ENABLE_DEV_LOGIN=false")

    for w in warnings:
        print(f"  [WARN] {w}")
    for f in failures:
        print(f"  [FAIL] {f}")

    if failures:
        print("\nStaging NOT ready — fix backend/.env before deploy.")
        return 1

    print("\nStaging env looks ready for Phase A deploy.")
    print(
        "Next: docker compose -f docker-compose.yml -f docker-compose.staging.yml "
        "-f docker-compose.prod.yml up -d --build"
    )
    print("Then: ./scripts/run-staging-acceptance.sh $BACKEND_URL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
