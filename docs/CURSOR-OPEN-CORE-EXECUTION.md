# Cursor Open Core Execution Guide

Use this guide to implement the Open Core restructuring safely.

## PR 1 — Add Open Core Policy

Prompt:

```text
Add Open Core policy docs and README links.

Do not change the license file.
Do not remove existing quick start or demo docs.
Add links to OPEN-CORE.md, LICENSE-POLICY.md, COMMERCIAL.md, SECURITY.md, DATA-CONSENT.md, ANTI-ABUSE-POLICY.md, REPOSITORY-BOUNDARY.md, OPEN-SOURCE-ROADMAP.md, and COMMERCIAL-MODULES.md.
```

## PR 2 — Format Backend Source

Prompt:

```text
Format backend Python source files for readability.

Add or use black and ruff if appropriate.
Do not change business logic.
Ensure smoke tests still pass.
```

## PR 3 — License Review

Prompt:

```text
Review current license and prepare a license migration proposal.

Do not change LICENSE automatically.
Add an issue or doc explaining migration from MIT to Apache-2.0 for core code and CC BY 4.0 for protocol docs.
```

## PR 4 — Security Process

Prompt:

```text
Add GitHub security reporting process.

Ensure SECURITY.md is linked from README.
Do not expose exploit details or private anti-abuse logic.
```

## PR 5 — Repository Split Planning

Prompt:

```text
Add repository split roadmap.

Define public repos, semi-open repos, and private commercial repos.
Mark deprecated repos clearly.
```

PoCP begins with contribution.
