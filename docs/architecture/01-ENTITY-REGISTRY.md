# Entity Registry

## Purpose

The Entity Registry records every participant in the PoCP Neural Commons Network.

## Entity Types

- Human
- Agent
- LLM
- Skill
- Tool
- Dataset
- Workflow
- Compute Node
- Verifier Node
- Reviewer Node
- Organization
- Community
- Sponsor
- Protocol Treasury

## Core Fields

```text
entity_id
entity_type
name
owner
status
capabilities
wallet
reputation
risk_level
created_at
updated_at
metadata
```

## Principle

Entity is the root object of PoCP.

PoCP begins with contribution.

---

## Platform catalog bootstrap

`backend/services/entity_catalog.py` idempotently ensures:

- All **14 ontology types** have at least one representative Entity
- Stable infrastructure IDs (compute, verifier, reviewer, sponsor, treasury, workflow)
- Capability registry completeness (≥ 11 seeded capabilities)
- Cross-linked metadata on org / Rain entities for discovery

On catalog repair, infrastructure Entities also receive **NodeProfile** rows (Layer 2) — see [NODE-RUNTIME-SPEC.md](../protocol/NODE-RUNTIME-SPEC.md).

Frozen CI-1 → CI-2 mapping:

- Entity IDs: `backend/services/entity/schemas.py` (`INFRASTRUCTURE_ENTITY_IDS`, `NODE_ELIGIBLE_INFRASTRUCTURE_IDS`)
- Catalog boundary: `backend/services/entity/base.py` (`EntityCatalogRegistry`)
- Node types: `backend/services/node/schemas.py` (`CATALOG_NODE_TYPE_BY_ENTITY`, `catalog_node_specs()`)
- Well-known draft: `build_instance_endpoints()` + `GET /.well-known/pocp-node.json` ([PUBLIC-NODE-PROTOCOL.md](../protocol/PUBLIC-NODE-PROTOCOL.md))

```bash
python backend/scripts/audit_entities.py --repair
```
