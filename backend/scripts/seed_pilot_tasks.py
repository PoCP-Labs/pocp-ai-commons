"""Seed Entity Network Pilot task templates from config/pilot_tasks.yaml.

Usage:
  python scripts/seed_pilot_tasks.py --api http://127.0.0.1:8000
  cd backend && python scripts/seed_pilot_tasks.py --db
  python scripts/seed_pilot_tasks.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import SessionLocal
from models.entity import Entity
from models.task import Task, TaskStatus
from services.org_foundation import POCP_ORG_NAME, ensure_pocp_org_foundation

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "pilot_tasks.yaml"


def _format_description(task: dict) -> str:
    lines = [task.get("description", "").strip()]
    meta = [
        f"Type: {task.get('type', 'general')}",
        f"StudyAgent: {'allowed' if task.get('study_agent_allowed') else 'manual only'}",
        f"Suggested CP: {task.get('suggested_cp', '—')}",
        f"Suggested AI Credits: {task.get('suggested_ai_credits', '—')}",
    ]
    acceptance = task.get("acceptance") or []
    if acceptance:
        meta.append("Acceptance criteria:")
        meta.extend(f"  - {item}" for item in acceptance)
    lines.append("")
    lines.extend(meta)
    return "\n".join(lines).strip()


def _load_spec() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _http_json(method: str, url: str, body: dict | None = None, token: str | None = None) -> dict | list:
    headers = {"Content-Type": "application/json"} if body else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode())


def seed_pilot_tasks_via_api(base: str, *, dry_run: bool = False) -> dict:
    spec = _load_spec()
    sponsor_name = spec.get("sponsor_org_name") or POCP_ORG_NAME
    root = base.rstrip("/")

    login = _http_json(
        "POST",
        f"{root}/api/v1/auth/dev-login",
        {"username": "rain", "email": "rain@example.com"},
    )
    token = login["access_token"]

    entities = _http_json("GET", f"{root}/api/v1/entities")
    sponsor = next((e for e in entities if e.get("name") == sponsor_name), None)
    if sponsor is None:
        raise RuntimeError(f"Sponsor org '{sponsor_name}' not found on {base}")

    existing_tasks = _http_json("GET", f"{root}/api/v1/tasks")
    existing_titles = {t.get("title") for t in existing_tasks}

    created = 0
    skipped = 0
    for task in spec.get("tasks") or []:
        title = task.get("title", "").strip()
        if not title:
            continue
        if title in existing_titles:
            skipped += 1
            continue
        if dry_run:
            print(f"would create: {title}")
            created += 1
            continue
        _http_json(
            "POST",
            f"{root}/api/v1/tasks",
            {
                "title": title,
                "description": _format_description(task),
                "sponsor_id": sponsor["id"],
            },
            token=token,
        )
        created += 1

    return {"created": created, "skipped": skipped, "config": str(CONFIG_PATH), "mode": "api"}


def seed_pilot_tasks_db(*, dry_run: bool = False) -> dict:
    spec = _load_spec()
    db = SessionLocal()
    created = 0
    skipped = 0
    try:
        sponsor_name = spec.get("sponsor_org_name") or POCP_ORG_NAME
        sponsor = db.query(Entity).filter(Entity.name == sponsor_name).first()
        if sponsor is None:
            from genesis import ensure_genesis_entities
            from seed import seed_demo

            ensure_genesis_entities(db)
            seed_demo(db)
            db.commit()
            sponsor = db.query(Entity).filter(Entity.name == sponsor_name).first()
        ensure_pocp_org_foundation(db)
        if sponsor is None:
            raise RuntimeError(
                f"Sponsor org '{sponsor_name}' not found — start API once to seed demo data."
            )

        for task in spec.get("tasks") or []:
            title = task.get("title", "").strip()
            if not title:
                continue
            existing = db.query(Task).filter(Task.title == title).first()
            if existing:
                skipped += 1
                continue
            if dry_run:
                print(f"would create: {title}")
                created += 1
                continue
            db.add(
                Task(
                    title=title,
                    description=_format_description(task),
                    sponsor_id=sponsor.id,
                    status=TaskStatus.open,
                )
            )
            created += 1
        if not dry_run:
            db.commit()
    finally:
        db.close()

    return {"created": created, "skipped": skipped, "config": str(CONFIG_PATH), "mode": "db"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed pilot task templates")
    parser.add_argument("--api", metavar="URL", help="Seed via HTTP API (recommended)")
    parser.add_argument("--db", action="store_true", help="Seed via DATABASE_URL directly")
    parser.add_argument("--dry-run", action="store_true", help="Print tasks without writing")
    args = parser.parse_args()

    try:
        if args.api:
            summary = seed_pilot_tasks_via_api(args.api, dry_run=args.dry_run)
        elif args.db:
            summary = seed_pilot_tasks_db(dry_run=args.dry_run)
        else:
            summary = seed_pilot_tasks_via_api("http://127.0.0.1:8000", dry_run=args.dry_run)
    except urllib.error.URLError as exc:
        print(f"ERROR: API seed failed — {exc}", file=sys.stderr)
        print("Try: python scripts/seed_pilot_tasks.py --api http://127.0.0.1:8000", file=sys.stderr)
        sys.exit(2)

    print(
        f"Pilot tasks ({summary.get('mode', '?')}): created={summary['created']} "
        f"skipped={summary['skipped']} ({summary['config']})"
    )


if __name__ == "__main__":
    main()
