# Open Core Integration Guide

## Purpose

This guide helps Cursor and contributors integrate the Open Core strategy into the existing repository.

## Step 1 — Add policy docs

Add:

- OPEN-CORE.md
- LICENSE-POLICY.md
- COMMERCIAL.md
- SECURITY.md
- DATA-CONSENT.md
- ANTI-ABUSE-POLICY.md
- REPOSITORY-BOUNDARY.md
- OPEN-SOURCE-ROADMAP.md
- COMMERCIAL-MODULES.md

## Step 2 — Update README

Add an `Open Core Strategy` section.

Do not remove existing quick start, API, demo, or smoke test sections.

## Step 3 — Preserve license for now

Do not change the current LICENSE file automatically.

License migration should be a separate PR.

## Step 4 — Add issue templates

Add templates for:

- open core boundary;
- license policy;
- security policy;
- commercial boundary;
- repository split.

## Step 5 — Do not expose sensitive logic

Do not add advanced anti-abuse parameters, private risk model weights, commercial routing algorithms, compute scheduler optimization logic, or private deployment secrets into the public repo.

## Step 6 — Next PRs

Recommended next PRs:

1. Format backend Python source files.
2. Add CI for smoke tests.
3. Add Security reporting.
4. Add DCO or CLA policy.
5. Split protocol specification into a dedicated repo.

PoCP begins with contribution.
