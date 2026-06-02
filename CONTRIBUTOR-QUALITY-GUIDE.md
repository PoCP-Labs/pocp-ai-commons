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

**Phase A acceptance** (when touching core loop):

```bash
python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8000
# Federation:
python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101
```

Primary execution path: [docs/ROADMAP-THREE-PHASES.md](./docs/ROADMAP-THREE-PHASES.md).

**Local optimization P0** (Exchange Spine + Wallet — federation acceptance):

```bash
python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101
```

Exit signals: `federation_exchange_demo_test.py` green; `GET /wallets/audit` valid; constitution tests green. See [docs/protocol/README.md](./docs/protocol/README.md).

**Protocol layer (Entity Dialogue — P2, parallel track):**

```bash
cd backend && python -m pytest -q tests/test_entity_dialogue.py
```

Spec: [docs/protocol/ENTITY-DIALOGUE-PROTOCOL.md](./docs/protocol/ENTITY-DIALOGUE-PROTOCOL.md) · Mission: [agents/missions/protocol-layer-edp/MANIFEST.md](./agents/missions/protocol-layer-edp/MANIFEST.md).

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
