# Repository Boundary

## 1. Purpose

This document defines how PoCP-Labs should organize public, semi-open, and private repositories.

## 2. Current Public Repository

Current:

```text
pocp-ai-commons
```

Role:

```text
Open reference implementation and first application scenario.
```

Should include:

- basic backend;
- basic frontend;
- protocol docs;
- reference contribution loop;
- CP / AI Credits basic accounting;
- basic ledger;
- basic human review;
- basic reputation;
- basic graph;
- smoke tests;
- examples.

Should not include:

- advanced anti-abuse internals;
- commercial neural routing optimizer;
- managed compute scheduler;
- enterprise private deployment secrets;
- commercial API gateway;
- private customer logic;
- sensitive risk model parameters.

## 3. Recommended Public Repositories

```text
pocp-manifesto
pocp-protocol-spec
pocp-ai-commons
pocp-sdk-python
pocp-sdk-js
pocp-mcp-server
pocp-examples
```

## 4. Recommended Semi-Open Repositories

These may be open basic editions or delayed open source.

```text
pocp-neural-routing-basic
pocp-compute-adapter-basic
pocp-reputation-engine-basic
pocp-settlement-basic
```

## 5. Recommended Private / Commercial Repositories

```text
pocp-enterprise-console
pocp-anti-abuse-engine
pocp-commercial-router
pocp-compute-scheduler
pocp-risk-models
pocp-enterprise-api-gateway
pocp-private-deployment
```

## 6. Deprecated Repository Handling

If a repository is misspelled, obsolete, or experimental, mark it clearly:

```text
Deprecated. Please use pocp-ai-commons.
```

Or archive it.

## 7. Principle

Public repositories should build protocol trust and developer adoption.

Private repositories should protect security, commercial sustainability, and enterprise operations.

PoCP begins with contribution.
