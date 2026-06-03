# Entity Layer Spec

Entity is the network subject of PoCP.

Entity is not only a UserAccount.

Current AI Commons entities should be extended over time to include:

```text
human
agent
llm
skill
tool
dataset
workflow
organization
community
compute_node
verifier_node
reviewer_node
sponsor
protocol_treasury
```

Settlement, reputation, invocation, proof, and governance should bind to Entity.

---

## Platform entity catalog (CI-1)

Phase A bootstrap: `backend/services/entity_catalog.py` · ontology: `backend/intelligence/entity_ontology.py`.

Frozen CI-1 contract: `backend/services/entity/schemas.py` (`INFRASTRUCTURE_ENTITY_IDS`, stable ID constants).

| Concern | Module | Output |
|---------|--------|--------|
| Type coverage | `audit_entity_catalog()` | 14 ontology types present |
| Infrastructure IDs | `ensure_platform_entity_catalog()` | Stable compute / verifier / reviewer / sponsor / treasury / workflow |
| Capability seeds | `seed_platform_capabilities()` | Genesis + infrastructure capability rows |
| Metadata cross-links | `_link_catalog_metadata()` | Org ↔ infrastructure ID pointers |
| Node layer handoff | `_ensure_node_profiles()` | NodeProfile rows for infrastructure entities → [NODE-RUNTIME-SPEC.md](./NODE-RUNTIME-SPEC.md) |

Stable infrastructure entity IDs (do not rename without migration):

```text
pocp-entity-local-compute
pocp-entity-local-verifier
pocp-entity-bob-reviewer
pocp-entity-rain-sponsor
pocp-entity-protocol-treasury
pocp-entity-study-workflow
```

**Node-eligible subset** (`NODE_ELIGIBLE_INFRASTRUCTURE_IDS` in `backend/services/entity/schemas.py`) — all except `pocp-entity-study-workflow` (workflow Entity has no public NodeProfile).

| Entity ID | Node type (CI-2) |
|-----------|------------------|
| `pocp-entity-local-compute` | `compute` |
| `pocp-entity-local-verifier` | `verifier` |
| `pocp-entity-bob-reviewer` | `reviewer` |
| `pocp-entity-rain-sponsor` | `service` |
| `pocp-entity-protocol-treasury` | `treasury` |

Forge target: `entity_catalog._ensure_node_profiles()` SHOULD call `catalog_node_specs(backend_url=…)` from `backend/services/node/schemas.py` (single source of truth).

Audit:

```bash
python backend/scripts/audit_entities.py --repair
```
