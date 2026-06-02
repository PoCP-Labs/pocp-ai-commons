# Commercial Reserved Boundary

## Purpose

This document defines what should not be placed into the public core repository.

## Reserved Commercial / Sensitive Areas

### 1. Advanced Anti-Abuse Intelligence

Do not open-source:

- fraud graph model weights;
- CP farming detection thresholds;
- AI Credits farming patterns;
- Sybil detection signals;
- collusion scoring;
- replay attack private signatures;
- blacklists;
- abuse risk weights.

### 2. Commercial Neural Routing

Do not open-source:

- commercial routing optimizer;
- high-value capability ranking algorithm;
- enterprise SLA routing;
- GPU price arbitrage logic;
- advanced task-to-agent matching;
- private routing policies.

### 3. Managed Compute Scheduler

Do not open-source:

- provider price strategy;
- node selection optimizer;
- SLA enforcement logic;
- commercial GPU scheduler;
- supplier integration secrets;
- compute reliability private model.

### 4. Enterprise Governance Console

Do not open-source:

- enterprise customer workflows;
- private governance rules;
- enterprise permission model;
- compliance dashboard internals;
- customer-specific audit logic.

### 5. Commercial API Gateway

Do not open-source:

- billing logic;
- enterprise quota logic;
- commercial API keys;
- partner billing rules;
- paid usage analytics internals.

### 6. Advanced Reputation / Risk Models

Do not open-source:

- production reputation weights;
- reviewer accuracy model;
- agent reliability private scoring;
- skill ranking commercial logic;
- graph propagation weights;
- risk model calibration.

## What Can Be Public

For each reserved area, the public repo may contain:

- interface;
- schema;
- basic reference implementation;
- mock implementation;
- example adapter;
- documentation;
- tests for basic behavior.

## Principle

Keep trust-critical rules open.

Keep exploit-sensitive and commercial optimization logic reserved.

PoCP begins with contribution.
