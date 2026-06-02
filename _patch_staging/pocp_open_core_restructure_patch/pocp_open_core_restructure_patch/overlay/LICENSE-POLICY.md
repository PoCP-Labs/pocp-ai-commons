# License Policy

## 1. Current State

The current public repository may use a permissive open-source license such as MIT.

This is acceptable for early experimentation, but PoCP's long-term role as protocol infrastructure requires a clearer licensing strategy.

## 2. Recommended License Structure

### Protocol Documents

Recommended license:

```text
CC BY 4.0
```

Applies to:

- protocol specifications;
- manifesto;
- architecture documents;
- governance principles;
- token measurement documents;
- whitepapers.

Why:

- allows broad reuse;
- requires attribution;
- supports protocol spread.

### Core Reference Implementation

Recommended license:

```text
Apache-2.0
```

Applies to:

- backend;
- frontend;
- reference implementation;
- SDKs;
- CLI;
- MCP server;
- adapters;
- examples.

Why:

- permissive;
- enterprise-friendly;
- includes explicit patent grant;
- better suited for protocol infrastructure than MIT.

### SDKs

Recommended license:

```text
Apache-2.0 or MIT
```

SDKs should be easy to adopt.

### Commercial Modules

Recommended license:

```text
Commercial License
```

Applies to:

- enterprise governance console;
- commercial neural routing;
- managed compute scheduler;
- advanced anti-abuse intelligence;
- commercial API gateway;
- private deployment tools;
- advanced reputation and risk models.

## 3. Do Not Change License Casually

If external contributors have contributed code, changing license may require contributor agreement or explicit consent.

Before changing the current repository license:

1. review contribution history;
2. identify external contributors;
3. confirm legal ownership and consent;
4. open an issue for discussion;
5. update LICENSE and README;
6. document the transition.

## 4. Recommended Path

Short term:

```text
Keep current license.
Add this License Policy.
Clarify commercial modules are separate.
```

Medium term:

```text
Move core reference implementation to Apache-2.0.
Use CC BY 4.0 for protocol docs.
Use Commercial License for enterprise modules.
```

Long term:

```text
Create clear contributor license agreement or Developer Certificate of Origin process.
```

## 5. Principle

The license should support adoption, trust, and sustainability.

PoCP begins with contribution.
