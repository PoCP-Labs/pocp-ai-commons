# Contributor Quality Guide

## Purpose

This guide explains how contributors should work on the public PoCP core.

## Contribution Priorities

Current priority:

```text
Make the public core readable, runnable, auditable, and contributor-friendly.
```

Before adding large new features, contributors should help with:

- formatting;
- tests;
- README consistency;
- health checks;
- docs;
- basic reference implementations;
- issue clarity;
- PR quality.

## Code Rules

- Keep code readable.
- Preserve existing demo behavior.
- Do not introduce commercial-only internals.
- Do not include secrets.
- Add tests or manual verification steps.
- Keep PRs small.
- Mark mock/reference implementations clearly.

## PR Requirements

Every PR should include:

- purpose;
- scope;
- files changed;
- tests run;
- screenshots if frontend changes;
- open-core boundary note if relevant.

## AI-Assisted Contributions

AI-assisted contributions are welcome, but must be human-reviewed.

If AI was used heavily, disclose it briefly in the PR.

## Public vs Commercial Boundary

Do not contribute:

- advanced anti-abuse scoring;
- private risk weights;
- commercial routing optimizer;
- enterprise customer logic;
- secret-based deployment scripts;
- paid API gateway internals.

You may contribute:

- basic reference implementations;
- interfaces;
- schemas;
- mock adapters;
- tests;
- docs;
- SDK examples.

## Principle

Contribution should be visible, verifiable, and responsible.

PoCP begins with contribution.
