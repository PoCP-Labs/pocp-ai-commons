# Open Source Roadmap

## Phase 1 — Open Core Foundation

Goals:

- define open-core strategy;
- add license policy;
- add commercial boundary;
- add security policy;
- add data consent policy;
- add anti-abuse policy;
- add repository boundary.

Deliverables:

- OPEN-CORE.md
- LICENSE-POLICY.md
- COMMERCIAL.md
- SECURITY.md
- DATA-CONSENT.md
- ANTI-ABUSE-POLICY.md
- REPOSITORY-BOUNDARY.md

## Phase 2 — Engineering Health

Goals:

- format backend source;
- add formatter config;
- add linting;
- ensure smoke tests pass;
- improve PR readability;
- add CI.

Deliverables:

- black / ruff config;
- formatted Python files;
- GitHub Actions;
- smoke test in CI.

## Phase 3 — Public Protocol Split

Goals:

- create dedicated protocol specification repository;
- clarify protocol document license;
- add schema files;
- add API examples.

Suggested repo:

```text
pocp-protocol-spec
```

## Phase 4 — SDK and Integration

Goals:

- create SDK repositories;
- build Python SDK;
- build TypeScript SDK;
- build MCP server;
- build examples.

Suggested repos:

```text
pocp-sdk-python
pocp-sdk-js
pocp-mcp-server
pocp-examples
```

## Phase 5 — Commercial Boundary

Goals:

- move advanced anti-abuse to private repo;
- move commercial routing to private repo;
- move enterprise console to private repo;
- move compute scheduler to private repo.

Suggested private repos:

```text
pocp-anti-abuse-engine
pocp-commercial-router
pocp-enterprise-console
pocp-compute-scheduler
```

## Phase 6 — Community Governance

Goals:

- add governance process;
- add contributor license or DCO;
- add maintainers file;
- define release process;
- define security disclosure process.

PoCP begins with contribution.
