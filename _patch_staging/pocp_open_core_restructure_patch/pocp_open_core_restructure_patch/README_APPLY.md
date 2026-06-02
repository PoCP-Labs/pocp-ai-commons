# PoCP Open Core Restructure Patch

This patch helps PoCP-Labs restructure the project into an **Open Core** model:

> Open protocol + open reference implementation + open SDKs + commercial intelligence / compute / enterprise layer.

It does not close the existing public repository. Instead, it clearly defines what remains open source, what is commercial, what is sensitive, and how future repositories should be split.

## What this patch adds

### Strategy and policy docs

- `OPEN-CORE.md`
- `LICENSE-POLICY.md`
- `COMMERCIAL.md`
- `SECURITY.md`
- `DATA-CONSENT.md`
- `ANTI-ABUSE-POLICY.md`
- `REPOSITORY-BOUNDARY.md`
- `OPEN-SOURCE-ROADMAP.md`
- `COMMERCIAL-MODULES.md`
- `docs/OPEN-CORE-INTEGRATION-GUIDE.md`
- `docs/CURSOR-OPEN-CORE-EXECUTION.md`

### GitHub issue templates

- `.github/ISSUE_TEMPLATE/open_core_boundary_task.md`
- `.github/ISSUE_TEMPLATE/license_policy_task.md`
- `.github/ISSUE_TEMPLATE/security_policy_task.md`
- `.github/ISSUE_TEMPLATE/commercial_boundary_task.md`
- `.github/ISSUE_TEMPLATE/repository_split_task.md`

### Helper files

- `apply_open_core_restructure_patch.py`
- `CURSOR_APPLY_PROMPT.md`

## How to apply

From the root of your local `pocp-ai-commons` repository:

```bash
python /path/to/pocp_open_core_restructure_patch/apply_open_core_restructure_patch.py
```

Then open Cursor and paste `CURSOR_APPLY_PROMPT.md`.

## Suggested branch

```bash
git checkout -b open-core-restructure
git add .
git commit -m "Add Open Core strategy and repository boundary policy"
git push origin open-core-restructure
```

## Important

This patch does not remove existing code.

It adds governance, licensing, open-source boundary, commercial boundary, security, data consent, and repository split planning.
