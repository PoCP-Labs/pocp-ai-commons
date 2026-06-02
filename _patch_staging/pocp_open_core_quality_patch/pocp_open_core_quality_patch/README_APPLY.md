# PoCP Open Core Quality Patch

This patch is designed for the current public `pocp-ai-commons` repository.

Goal:

> Keep the PoCP protocol skeleton open source, keep commercial intelligence capabilities reserved, and first turn the public repository into a high-quality open-source core.

This patch focuses on repository health, contribution quality, README consistency, basic open-core boundaries, formatter setup, CI scaffolding, and Cursor execution guidance.

## What this patch adds

### Repository health docs

- `OPEN-SOURCE-CORE-QUALITY.md`
- `REFERENCE-IMPLEMENTATION.md`
- `PUBLIC-CORE-BOUNDARY.md`
- `COMMERCIAL-RESERVED-BOUNDARY.md`
- `REPO-HEALTH-CHECKLIST.md`
- `CONTRIBUTOR-QUALITY-GUIDE.md`
- `docs/README-CONSISTENCY-CHECK.md`
- `docs/FORMATTER-AND-CI-GUIDE.md`
- `docs/OPEN-CORE-NEXT-PRS.md`

### Engineering files

- `pyproject.toml`
- `.editorconfig`
- `.github/workflows/backend-ci.yml`
- `backend/scripts/health_check.py`

### GitHub process files

- `.github/pull_request_template.md`
- `.github/ISSUE_TEMPLATE/repository_health_task.md`
- `.github/ISSUE_TEMPLATE/formatting_task.md`
- `.github/ISSUE_TEMPLATE/readme_consistency_task.md`
- `.github/ISSUE_TEMPLATE/public_core_boundary_task.md`

### Helper files

- `apply_open_core_quality_patch.py`
- `CURSOR_APPLY_PROMPT.md`

## How to apply

From the root of your local `pocp-ai-commons` repository:

```bash
python /path/to/pocp_open_core_quality_patch/apply_open_core_quality_patch.py
```

Then open Cursor and paste `CURSOR_APPLY_PROMPT.md`.

## Suggested branch

```bash
git checkout -b open-core-quality-core
git add .
git commit -m "Improve public open-source core quality and boundaries"
git push origin open-core-quality-core
```

## What this patch does not do

- It does not move code into private repositories.
- It does not change the current license automatically.
- It does not implement commercial anti-abuse, commercial routing, or compute scheduling.
- It does not introduce public token issuance.
- It does not break the current Genesis demo intentionally.
