# PoCP Neural Commons Network Full Patch

This patch restructures the project direction around:

> **PoCP Neural Commons Network** — a protocol-based distributed intelligence and compute network powered by verified contribution, tokenized measurement, capability routing, settlement, and entity reputation.

It keeps **PoCP AI Commons** as the first application scenario, but upgrades the long-term architecture to the full Neural Commons vision.

## What this patch adds

### Core strategy docs

- `POCP-NEURAL-COMMONS-NETWORK.md`
- `README-NEURAL-COMMONS.md`
- `NEURAL-COMMONS-MASTER-PLAN.md`
- `NEURAL-COMMONS-ROADMAP.md`
- `NEURAL-COMMONS-PR-PLAN.md`

### Architecture docs

- `docs/architecture/01-ENTITY-REGISTRY.md`
- `docs/architecture/02-CAPABILITY-REGISTRY.md`
- `docs/architecture/03-NEURAL-ROUTING.md`
- `docs/architecture/04-INVOCATION-LEDGER.md`
- `docs/architecture/05-VERIFICATION-PROOF.md`
- `docs/architecture/06-TOKEN-MEASUREMENT.md`
- `docs/architecture/07-SETTLEMENT-LAYER.md`
- `docs/architecture/08-REPUTATION-GOVERNANCE.md`
- `docs/architecture/09-NEURAL-GRAPH.md`

### Protocol specs

- `docs/protocol/ENTITY-SCHEMA-v0.3.md`
- `docs/protocol/CAPABILITY-SCHEMA-v0.3.md`
- `docs/protocol/INVOCATION-SCHEMA-v0.3.md`
- `docs/protocol/SETTLEMENT-SCHEMA-v0.3.md`
- `docs/protocol/TOKEN-MEASUREMENT-SCHEMA-v0.3.md`
- `docs/protocol/COMPUTE-NODE-SCHEMA-v0.3.md`

### Implementation docs

- `docs/implementation/CURSOR-NEURAL-COMMONS-EXECUTION.md`
- `docs/implementation/MIGRATION-FROM-AI-COMMONS.md`
- `docs/implementation/BACKEND-MODULE-PLAN.md`
- `docs/implementation/FRONTEND-MODULE-PLAN.md`
- `docs/implementation/API-ENDPOINT-PLAN.md`

### Backend skeletons

- `backend/services/neural/base.py`
- `backend/services/neural/rule_based_router.py`
- `backend/services/capability/base.py`
- `backend/services/token_measurement/base.py`
- `backend/services/settlement/base.py`
- `backend/services/compute/base.py`

### GitHub process

- `.github/ISSUE_TEMPLATE/neural_commons_task.md`
- `.github/ISSUE_TEMPLATE/capability_registry_task.md`
- `.github/ISSUE_TEMPLATE/token_measurement_task.md`
- `.github/ISSUE_TEMPLATE/settlement_layer_task.md`
- `.github/ISSUE_TEMPLATE/compute_node_task.md`
- `.github/ISSUE_TEMPLATE/reputation_governance_task.md`
- `.github/workflows/neural-commons-docs-check.yml`

### Helper

- `CURSOR_APPLY_PROMPT.md`
- `apply_neural_commons_network_patch.py`

## How to apply

From your local `pocp-ai-commons` repository root:

```bash
python /path/to/pocp_neural_commons_network_full_patch/apply_neural_commons_network_patch.py
```

Then paste `CURSOR_APPLY_PROMPT.md` into Cursor.

## Suggested branch

```bash
git checkout -b neural-commons-network-architecture
git add .
git commit -m "Add PoCP Neural Commons Network architecture"
git push origin neural-commons-network-architecture
```
