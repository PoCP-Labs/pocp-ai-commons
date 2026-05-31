#!/usr/bin/env python3
"""Create Epic A sub-issues (A1–A8) linked to GitHub issue #31."""

from __future__ import annotations

import subprocess
import sys

REPO = "PoCP-Labs/pocp-ai-commons"
EPIC_ISSUE = 31
BASE = f"https://github.com/{REPO}/blob/main"

SUBTASKS: list[dict] = [
    {
        "id": "A1",
        "title": "[Epic A] A1 — docker compose up healthy (Postgres + API + frontend)",
        "labels": ["sprint-alpha", "phase-a", "help wanted", "infra"],
        "body": f"""Part of Epic A #{EPIC_ISSUE}

## Goal

Fresh clone runs full stack with one command:

```bash
docker compose up --build
```

## Acceptance criteria

- [ ] Postgres becomes healthy before API starts
- [ ] API serves `/health` with `database.status: ok`
- [ ] Frontend reachable at `http://localhost:3000`
- [ ] Alembic migrations apply on boot; demo seed loads
- [ ] Documented in [LOCAL-SETUP.md]({BASE}/docs/LOCAL-SETUP.md)

## Test plan

```bash
git clone https://github.com/PoCP-Labs/pocp-ai-commons.git
cd pocp-ai-commons
docker compose up --build -d
curl -s http://localhost:8000/health
curl -s -o /dev/null -w "%{{http_code}}" http://localhost:3000
```
""",
    },
    {
        "id": "A2",
        "title": "[Epic A] A2 — smoke_test.py passes on :8000",
        "labels": ["sprint-alpha", "phase-a", "help wanted", "testing"],
        "body": f"""Part of Epic A #{EPIC_ISSUE}

## Goal

End-to-end API loop verified without manual curl steps:

```bash
cd backend && python scripts/smoke_test.py http://127.0.0.1:8000
```

## Acceptance criteria

- [ ] Smoke test exits 0 against Docker-backed API on port 8000
- [ ] Covers dev-login, wallet, contribution, auto-verify, approve, ledger
- [ ] CI workflow `.github/workflows/smoke-test.yml` green (if applicable)

## Depends on

- A1 (stack running)
""",
    },
    {
        "id": "A3",
        "title": "[Epic A] A3 — Validate production compose + PUBLIC-DEPLOY",
        "labels": ["sprint-alpha", "phase-a", "infra", "documentation"],
        "body": f"""Part of Epic A #{EPIC_ISSUE}

## Goal

Operator can deploy HTTPS production stack per [PUBLIC-DEPLOY.md]({BASE}/docs/PUBLIC-DEPLOY.md).

## Acceptance criteria

- [ ] `docker-compose.prod.yml` — Postgres **not** exposed on host 5432
- [ ] `backend/.env.production.example` aligns with prod compose
- [ ] `VITE_API_URL` baked correctly in frontend prod build
- [ ] Staging or checklist doc confirms Caddy/TLS steps
- [ ] Optional: add [PILOT-LAUNCH-CHECKLIST.md]({BASE}/docs/PUBLIC-DEPLOY.md) cross-links if missing

## Test plan

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml config
curl -s http://127.0.0.1:8000/health
```
""",
    },
    {
        "id": "A4",
        "title": "[Epic A] A4 — GitHub OAuth on staging (dev-login off)",
        "labels": ["sprint-alpha", "phase-a", "auth"],
        "body": f"""Part of Epic A #{EPIC_ISSUE}

## Goal

Public/staging instance uses GitHub Login with `ENABLE_DEV_LOGIN=false`.

## Acceptance criteria

- [ ] GitHub OAuth App callback matches `GITHUB_OAUTH_CALLBACK_URL`
- [ ] Login creates/links Human Entity + wallet
- [ ] Dev-login disabled on public host
- [ ] Document OAuth app settings in [PUBLIC-DEPLOY.md]({BASE}/docs/PUBLIC-DEPLOY.md)

## Notes

Requires staging domain or documented operator setup.
""",
    },
    {
        "id": "A5",
        "title": "[Epic A] A5 — Anti-abuse baseline tests",
        "labels": ["sprint-alpha", "phase-a", "testing", "security"],
        "body": f"""Part of Epic A #{EPIC_ISSUE}

## Goal

Confirm minimal anti-abuse guards work under test.

## Acceptance criteria

- [ ] Contribution without evidence rejected
- [ ] Daily contribution limit enforced (`DAILY_CONTRIBUTION_LIMIT`)
- [ ] Daily AI Credits burn limit enforced
- [ ] Self-approval blocked (submitter cannot approve own contribution)
- [ ] Tests or smoke assertions document expected behavior

## Related

- `backend/services/anti_abuse.py`
- [AI-CREDITS-GUIDE.md]({BASE}/docs/AI-CREDITS-GUIDE.md)
""",
    },
    {
        "id": "A6",
        "title": "[Epic A] A6 — Contribution graph semantics fix",
        "labels": ["sprint-alpha", "phase-a", "frontend", "help wanted"],
        "body": f"""Part of Epic A #{EPIC_ISSUE}

## Goal

Graph shows correct collaboration flow:

```text
Human —uses→ Agent —calls→ Skill —invokes_llm→ LLM
Verifiers / reviewers → contribution hub (not confusing cross-edges)
```

## Acceptance criteria

- [ ] No duplicate invocation traces in seed (single `record_invocation` per contribution)
- [ ] `backend/services/graph.py` — participant edges use contribution hub semantics
- [ ] Frontend graph subtitle matches visible node/edge counts
- [ ] No misleading role labels (e.g. verifier text floating between wrong nodes)

## Related files

- `backend/services/graph.py`
- `backend/seed.py`
- `frontend/src/ContributionGraph.jsx`
""",
    },
    {
        "id": "A7",
        "title": "[Epic A] A7 — Ledger UI human-readable (raw JSON optional)",
        "labels": ["sprint-alpha", "phase-a", "frontend", "good first issue"],
        "body": f"""Part of Epic A #{EPIC_ISSUE}

## Goal

Dashboard ledger section readable for non-developers; raw audit JSON behind toggle.

## Acceptance criteria

- [ ] Event types shown in plain language (not only `trust_list_updated`)
- [ ] Summary fields for common payload types
- [ ] "Show raw audit data (JSON)" optional expand
- [ ] Brief hint: ledger record ≠ application source code

## Related

- `frontend/src/App.jsx` — `LedgerBlockPanel`
""",
    },
    {
        "id": "A8",
        "title": "[Epic A] A8 — README / LOCAL-SETUP troubleshooting",
        "labels": ["sprint-alpha", "phase-a", "documentation", "good first issue"],
        "body": f"""Part of Epic A #{EPIC_ISSUE}

## Goal

New contributors resolve common setup failures without maintainer help.

## Acceptance criteria

- [ ] [LOCAL-SETUP.md]({BASE}/docs/LOCAL-SETUP.md) — Docker not running, port conflicts, DB reset
- [ ] README Quick Start matches actual ports and URLs
- [ ] Link to Epic tracker [TOKEN-PATHWAY-EPICS.md]({BASE}/docs/TOKEN-PATHWAY-EPICS.md)
- [ ] Windows notes if applicable (Docker Desktop, PowerShell)

## Trigger

Update after A1/A2 pilot feedback from first external setup attempts.
""",
    },
]


def ensure_labels(names: list[str]) -> None:
    for name in names:
        subprocess.run(
            ["gh", "label", "create", name, "--force", "--repo", REPO],
            capture_output=True,
            text=True,
        )


def issue_exists(title: str) -> bool:
    result = subprocess.run(
        ["gh", "issue", "list", "--repo", REPO, "--search", f'"{title}" in:title', "--limit", "5", "--json", "title"],
        capture_output=True,
        text=True,
        check=True,
    )
    return title in result.stdout


def create_issue(title: str, labels: list[str], body: str) -> str:
    cmd = ["gh", "issue", "create", "--repo", REPO, "--title", title, "--body", body]
    for label in labels:
        cmd.extend(["--label", label])
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def main() -> int:
    all_labels = {label for task in SUBTASKS for label in task["labels"]}
    ensure_labels(sorted(all_labels))

    created: list[tuple[str, str, str]] = []
    for task in SUBTASKS:
        title = task["title"]
        if issue_exists(title):
            print(f"SKIP (exists): {task['id']} {title}")
            continue
        url = create_issue(title, task["labels"], task["body"])
        print(f"CREATED {task['id']}: {url}")
        created.append((task["id"], title, url))

    if created:
        checklist = "\n".join(f"- [ ] **{tid}** — {url}" for tid, _, url in created)
        subprocess.run(
            [
                "gh",
                "issue",
                "comment",
                str(EPIC_ISSUE),
                "--repo",
                REPO,
                "--body",
                f"## Sub-issues created\n\n{checklist}\n\nLink child PRs with `Part of #{EPIC_ISSUE}`.",
            ],
            check=True,
        )
        print(f"\nUpdated Epic #{EPIC_ISSUE} with sub-issue checklist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
