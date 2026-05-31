#!/usr/bin/env python3
"""Create GitHub Epic issues from .github/ISSUE_TEMPLATE/epic_*.md templates."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = REPO_ROOT / ".github" / "ISSUE_TEMPLATE"
REPO = "PoCP-Labs/pocp-ai-commons"
BASE = f"https://github.com/{REPO}/blob/main"


def parse_template(path: Path) -> tuple[str, list[str], str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError(f"Invalid template frontmatter: {path}")

    frontmatter, body = match.groups()
    title = ""
    labels: list[str] = []
    for line in frontmatter.splitlines():
        if line.startswith("title:"):
            title = line.split("title:", 1)[1].strip().strip('"')
        elif line.startswith("labels:"):
            raw = line.split("labels:", 1)[1].strip().strip('"')
            labels = [part.strip() for part in raw.split(",") if part.strip()]

    body = body.replace("../../", f"{BASE}/")
    return title, labels, body.strip()


def ensure_labels(names: list[str]) -> None:
    for name in names:
        subprocess.run(
            ["gh", "label", "create", name, "--force", "--repo", REPO],
            capture_output=True,
            text=True,
        )


def issue_exists(title: str) -> bool:
    result = subprocess.run(
        ["gh", "issue", "list", "--repo", REPO, "--search", f'"{title}" in:title', "--limit", "1", "--json", "title"],
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
    templates = sorted(TEMPLATE_DIR.glob("epic_*.md"))
    if not templates:
        print("No epic_*.md templates found.", file=sys.stderr)
        return 1

    all_labels: set[str] = set()
    parsed = []
    for path in templates:
        title, labels, body = parse_template(path)
        parsed.append((path.name, title, labels, body))
        all_labels.update(labels)

    ensure_labels(sorted(all_labels))

    created: list[tuple[str, str]] = []
    for name, title, labels, body in parsed:
        if issue_exists(title):
            print(f"SKIP (exists): {title}")
            continue
        url = create_issue(title, labels, body)
        print(f"CREATED: {url}")
        created.append((name, url))

    if created:
        print("\n--- Created issues ---")
        for name, url in created:
            print(f"  {name}: {url}")
    else:
        print("\nNo new issues created (all may already exist).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
