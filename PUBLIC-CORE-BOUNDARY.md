# Public Core Boundary

## Purpose

This document defines what belongs in the public PoCP core.

## Public Core

The following should be open source.

### Protocol and Schemas

- Entity schema
- Contribution schema
- Capability schema
- Invocation schema
- Wallet schema
- Ledger schema
- Settlement schema
- Reputation schema
- Governance schema

### Reference Implementation

- Basic backend
- Basic frontend
- Basic contribution flow
- Basic AI verifier
- Basic human review
- Basic CP / AI Credits accounting
- Basic ledger
- Basic reputation
- Basic graph
- Basic smoke tests

### Developer Integration

- API examples
- SDKs
- CLI
- MCP server
- adapters
- examples

### Governance and Policy

- Open Core strategy
- License policy
- Security policy
- Data consent policy
- Anti-abuse principles
- Contribution guide
- Code of conduct
- Human review principles

## Public Basic Modules

The public repo may include basic modules:

```text
anti_abuse/basic.py
routing/basic.py
reputation/basic.py
settlement/basic.py
compute/basic.py
```

These should be simple, explainable, and safe for reference use.

## Public Interfaces

The public repo may include interfaces for commercial modules:

```text
anti_abuse/base.py
routing/base.py
reputation/base.py
settlement/base.py
compute/base.py
```

Interfaces should not leak sensitive implementation logic.

## Principle

The public core should make PoCP understandable, auditable, and extensible.

PoCP begins with contribution.
