# Neural Commons Roadmap

Execution follows the **three-phase path** first: [docs/ROADMAP-THREE-PHASES.md](docs/ROADMAP-THREE-PHASES.md).

| Phase | Horizon | This roadmap |
|-------|---------|--------------|
| **A** | Now | v0.3 docs + demonstrable loop (acceptance runner) |
| **A→B** | Next | v0.4 Entity & Capability kernel |
| **B** | 2–4 mo | v0.5–v0.7 invocation, settlement, routing |
| **C** | 6–12 mo | SDK + unified capability market |

## v0.3 — Neural Commons Architecture

Focus:

- README repositioning;
- architecture docs;
- schema specs;
- PR plan;
- public core boundary.

Exit criteria:

- repository clearly communicates Neural Commons direction;
- PoCP AI Commons remains first application scenario;
- token language is careful;
- public vs commercial boundary is clear.

## v0.4 — Entity & Capability Kernel

Focus:

- Entity expansion;
- Compute Node;
- Verifier Node;
- Reviewer Node;
- Sponsor;
- Protocol Treasury;
- Capability model;
- Capability registry API.

Exit criteria:

- every major network participant can be represented;
- capabilities can be registered and queried.

Status (in progress):

- [x] Entity types extended to schema v0.3 (14 types)
- [x] `entity_capabilities` table + Alembic migration
- [x] `POST/GET /api/v1/registry/capabilities` register + search
- [ ] Bridge imported skills/agents into capability registry
- [ ] Protocol treasury bootstrap in genesis seed

## v0.5 — Invocation & Token Measurement

Focus:

- invocation records;
- AI usage records;
- compute usage records;
- internal TokenAccount;
- CP / AIC / CC / PT accounting;
- transaction ledger.

Exit criteria:

- capability usage can burn credits;
- capability contribution can create measurable records.

## v0.6 — Settlement Layer

Focus:

- SettlementRecord;
- multi-entity distribution;
- reviewer reward;
- verifier reward;
- sponsor pool;
- treasury flow;
- dispute status.

Exit criteria:

- a task can settle value across multiple participants.

## v0.7 — Neural Routing

Focus:

- task analyzer;
- capability matcher;
- rule-based execution planner;
- cost estimator;
- risk estimator;
- routing log.

Exit criteria:

- a task can be mapped to a basic execution plan.

## v0.8 — Verification & Reputation

Focus:

- verifier provider interface;
- human review;
- compute verification basic;
- reputation updates;
- anti-abuse basic;
- appeal / dispute docs.

Exit criteria:

- verified outcomes update reputation.

## v0.9 — Neural Graph Explorer

Focus:

- Entity graph;
- Capability graph;
- Invocation graph;
- Settlement graph;
- Reputation graph;
- Graph API.

Exit criteria:

- users can see how value was created and settled.

## v1.0 — Neural Commons MVP

Focus:

- end-to-end task flow;
- routing;
- invocation;
- verification;
- settlement;
- reputation;
- graph.

Exit criteria:

```text
Task
→ Route
→ Invoke
→ Execute
→ Verify
→ Review
→ Settle
→ Update Reputation
→ Show Graph
```

PoCP begins with contribution.
