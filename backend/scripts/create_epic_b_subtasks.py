#!/usr/bin/env python3
"""Create Epic B sub-issues (B1–B8) linked to GitHub issue #29."""

from __future__ import annotations

import subprocess
import sys

REPO = "PoCP-Labs/pocp-ai-commons"
EPIC_ISSUE = 29
BASE = f"https://github.com/{REPO}/blob/main"

SUBTASKS: list[dict] = [
    {
        "id": "B1",
        "title": "[Epic B] B1 — Publish 10–30 real pilot task templates",
        "labels": ["pilot", "phase-b", "documentation"],
        "body": f"""Part of Epic B #{EPIC_ISSUE}

## Goal

Curate real contribution tasks for pilot (study, OSS docs, community service).

## Acceptance criteria

- [ ] 10–30 tasks with acceptance criteria and suggested rewards
- [ ] Tasks published via API or documented seed/import process
- [ ] Aligned with [CONTRIBUTION-NEURAL-NETWORK.md]({BASE}/docs/CONTRIBUTION-NEURAL-NETWORK.md) demo scenarios

Depends on Epic A #{31} complete.
""",
    },
    {
        "id": "B2",
        "title": "[Epic B] B2 — Recruit ≥5 human reviewers",
        "labels": ["pilot", "phase-b", "governance"],
        "body": f"""Part of Epic B #{EPIC_ISSUE}

## Goal

Reviewer pool separate from primary contributors.

## Acceptance criteria

- [ ] ≥ 5 reviewers onboarded with [HUMAN-REVIEW-GUIDE.md]({BASE}/docs/HUMAN-REVIEW-GUIDE.md)
- [ ] Self-approval blocked in practice (different accounts)
""",
    },
    {
        "id": "B3",
        "title": "[Epic B] B3 — Pilot participant onboarding doc",
        "labels": ["pilot", "phase-b", "documentation", "good first issue"],
        "body": f"""Part of Epic B #{EPIC_ISSUE}

## Goal

One-page guide: GitHub login → wallet → AI Chat → task → submit → review.

## Acceptance criteria

- [ ] Linked from [PILOT-LAUNCH-CHECKLIST.md]({BASE}/docs/PILOT-LAUNCH-CHECKLIST.md)
- [ ] References [PUBLIC-DEMO.md]({BASE}/docs/PUBLIC-DEMO.md)
""",
    },
    {
        "id": "B4",
        "title": "[Epic B] B4 — Pilot metrics export or dashboard",
        "labels": ["pilot", "phase-b", "help wanted"],
        "body": f"""Part of Epic B #{EPIC_ISSUE}

## Goal

Weekly visibility: registrations, contributions, Credits burn, abuse 429s.

## Acceptance criteria

- [ ] Script or admin endpoint for weekly CSV/JSON export
- [ ] Documented in pilot checklist
""",
    },
    {
        "id": "B5",
        "title": "[Epic B] B5 — User fairness survey (pilot)",
        "labels": ["pilot", "phase-b"],
        "body": f"""Part of Epic B #{EPIC_ISSUE}

## Goal

Collect feedback on CP/Credits fairness and AI verifier usefulness.

## Acceptance criteria

- [ ] Survey template (GitHub Discussion or form)
- [ ] Results summarized in retrospective issue
""",
    },
    {
        "id": "B6",
        "title": "[Epic B] B6 — Anti-abuse review at 2 weeks",
        "labels": ["pilot", "phase-b", "security"],
        "body": f"""Part of Epic B #{EPIC_ISSUE}

## Goal

Review gaming patterns after 2 weeks of pilot traffic.

## Acceptance criteria

- [ ] Review evidence rejects, daily limits, self-approval attempts
- [ ] Unit tests green: `python -m unittest discover -s tests -p test_anti_abuse.py`
""",
    },
    {
        "id": "B7",
        "title": "[Epic B] B7 — Optional sponsor org (API quota / Credits)",
        "labels": ["pilot", "phase-b"],
        "body": f"""Part of Epic B #{EPIC_ISSUE}

## Goal

One organization sponsors AI Credits or task bounties — **no token**.

## Acceptance criteria

- [ ] Sponsor pool documented and transparent
- [ ] No financial return promises
""",
    },
    {
        "id": "B8",
        "title": "[Epic B] B8 — Pilot retrospective",
        "labels": ["pilot", "phase-b"],
        "body": f"""Part of Epic B #{EPIC_ISSUE}

## Goal

Decide: scale to Epic C/D, adjust rules, or pause.

## Acceptance criteria

- [ ] GitHub issue with metrics + lessons learned
- [ ] Epic C/D go/no-go decision recorded
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
    created = []
    for task in SUBTASKS:
        if issue_exists(task["title"]):
            print(f"SKIP (exists): {task['id']}")
            continue
        url = create_issue(task["title"], task["labels"], task["body"])
        print(f"CREATED {task['id']}: {url}")
        created.append((task["id"], url))
    if created:
        checklist = "\n".join(f"- [ ] **{tid}** — {url}" for tid, url in created)
        subprocess.run(
            ["gh", "issue", "comment", str(EPIC_ISSUE), "--repo", REPO, "--body", f"## Sub-issues created\n\n{checklist}"],
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
