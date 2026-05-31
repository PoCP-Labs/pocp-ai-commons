# Open Source Core Quality

## Purpose

PoCP's protocol skeleton should remain open source.

Before splitting commercial modules, the public repository must become a high-quality open-source core.

A high-quality public core should be:

- readable;
- runnable;
- auditable;
- testable;
- documented;
- contributor-friendly;
- clear about what is open and what is commercially reserved.

## Why This Matters

PoCP aims to become protocol infrastructure for verified contribution networks in the age of AI.

This requires public trust.

Public trust depends on:

- transparent schemas;
- readable code;
- clear contribution flow;
- visible ledger logic;
- basic verification and review logic;
- clear license policy;
- security disclosure;
- data consent;
- anti-abuse principles;
- stable contribution process.

## Public Core Requirements

The public repository should maintain:

```text
Entity schema
Contribution schema
Capability / Invocation schema when added
Wallet / CP / AI Credits / Compute Credits basic accounting
Ledger record model
Human review reference flow
AI verifier reference flow
Basic reputation updates
Basic graph view
Smoke tests
Docker Compose
README and developer docs
```

## Quality Rules

### 1. Code must be readable

Python files must not be compressed into single-line files.

Use formatter tooling such as Black and Ruff.

### 2. Demo must remain runnable

The public repo should support a local demo path.

At minimum:

```bash
docker compose up --build
```

or:

```bash
cd backend
uvicorn main:app --reload
```

### 3. Smoke tests must exist

A public reference implementation must include tests or health checks.

### 4. README must match code

README should not describe files, routers, or APIs that are not present without saying they are target architecture.

### 5. Public core must not leak commercial internals

Do not include:

- private anti-abuse weights;
- commercial routing algorithms;
- compute scheduler optimization;
- enterprise customer configuration;
- private deployment secrets;
- commercial settlement parameters.

## Public Core vs Commercial Layer

PoCP should open the protocol skeleton and reference implementation.

PoCP may reserve advanced intelligence, security, routing, compute, enterprise, and commercial operations.

## Principle

Open the rules that build trust.

Protect the intelligence that defends and sustains the network.

PoCP begins with contribution.
