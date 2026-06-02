# Formatter and CI Guide

## Purpose

Open-source contributors need readable code and repeatable checks.

## Recommended Python Tools

- Black for formatting
- Ruff for linting
- Pytest for tests

## Local Commands

From repository root:

```bash
python backend/scripts/health_check.py
```

If backend environment is installed:

```bash
cd backend
python scripts/smoke_test.py http://127.0.0.1:8000
```

If Black and Ruff are installed:

```bash
black backend
ruff check backend --fix
```

## CI

This patch adds:

```text
.github/workflows/backend-ci.yml
```

The CI is conservative. It should not block basic docs-only work due to missing optional dependencies unless configured.

## Principle

Formatting is not cosmetic.

For an open-source protocol, readable code is part of trust.

PoCP begins with contribution.
