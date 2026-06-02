#!/usr/bin/env python3
"""Generate .cursor/skills/pocp-*/SKILL.md from Meta Agent specs."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from meta_agents_spec import META_AGENT_SPECS  # noqa: E402

SKILL_BODY = """# {name} — PoCP Meta Agent

**entity_id:** `{entity_id}`  
**Task label:** `{task_label}`  
**Reports to:** {reports_to}

## Activate

1. Read `agents/prompts/_global.md` (global rules).
2. Read `agents/prompts/{slug}.md` (full system prompt).
3. Obey `.cursor/rules/pocp-{slug}.mdc` when editing matching files.

## Role

{description}

## Capabilities

{capabilities_list}

## Writable paths (only)

```
{writable_paths_block}
```

## Handoff

On completion, return to **Nexus-0** (`pocp-agent-nexus-0`) with scope, files, tests, blockers.

Do **not** finalize CP/AI Credits on live contributions. Do **not** deploy staging without Anchor-H.

## API

- `GET /api/v1/meta-agents/{entity_id}` — registry record
- `POST /api/v1/meta-agents/ensure` — idempotent entity upsert
"""


def skill_dir_for_slug(slug: str) -> str:
    return slug.replace("-0", "")


def skill_frontmatter(spec: dict) -> str:
    slug = spec["slug"]
    skill_name = f"pocp-{skill_dir_for_slug(slug)}"
    desc = (
        f"PoCP {spec['name']} meta engineering agent ({spec['id']}). "
        f"Use for {', '.join(spec['roles'][:2])}. Task: {spec['task_label']}."
    )
    return f"""---
name: {skill_name}
description: {desc}
---

"""


def render_skill(spec: dict) -> str:
    caps = "\n".join(f"- `{c}`" for c in spec["capabilities"])
    paths = "\n".join(spec["writable_paths"])
    reports = spec["reports_to"] or "Anchor-H (human)"
    body = SKILL_BODY.format(
        name=spec["name"],
        entity_id=spec["id"],
        task_label=spec["task_label"],
        reports_to=reports,
        slug=spec["slug"],
        description=spec["description"],
        capabilities_list=caps,
        writable_paths_block=paths,
    )
    return skill_frontmatter(spec) + body


def main() -> int:
    skills_root = ROOT / ".cursor" / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)
    written = 0
    for spec in META_AGENT_SPECS:
        dir_name = f"pocp-{skill_dir_for_slug(spec['slug'])}"
        out_dir = skills_root / dir_name
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "SKILL.md"
        path.write_text(render_skill(spec), encoding="utf-8")
        written += 1
        print(f"wrote {path.relative_to(ROOT)}")
    print(f"Done: {written} Cursor skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
