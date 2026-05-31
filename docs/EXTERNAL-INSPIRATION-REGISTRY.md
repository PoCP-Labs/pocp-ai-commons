# External Inspiration Registry

PoCP records **borrowed open-source patterns** as **community entities** with documented contributions. This complements [CODE-CONTRIBUTION-REGISTRY.md](./CODE-CONTRIBUTION-REGISTRY.md) (who built PoCP code) and [EXTERNAL-INTEGRATIONS.md](./EXTERNAL-INTEGRATIONS.md) (how patterns map to APIs).

## Principles

- **Pattern borrowed, not forked** — we adapt ideas under [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md)
- **Entity transparency** — each inspiration gets a stable `entity_id` and optional `portable_id`
- **Contribution records** — each borrowed pattern is a row in `external_inspiration_records`
- **Declined projects recorded** — evaluated-but-not-imported projects appear under `declined_inspirations`

## Registry file

`backend/config/external_inspirations.yaml`

| Field | Meaning |
|-------|---------|
| `inspirations.<slug>.entity_id` | PoCP entity UUID-style id |
| `portable_id` | Cross-node identifier (e.g. `github:openoctp/spec`) |
| `contributions[]` | What PoCP borrowed: modules, APIs, proof layers |
| `declined_inspirations` | Projects we chose not to import (with reason) |

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/external-inspirations/registry` | Registry metadata |
| GET | `/api/v1/external-inspirations/inspirations` | All inspirations |
| GET | `/api/v1/external-inspirations/inspirations/{slug}` | One inspiration + contributions |
| GET | `/api/v1/external-inspirations/report` | Full transparency report |
| GET | `/api/v1/external-inspirations/records` | Persisted DB records |
| POST | `/api/v1/external-inspirations/match` | Match module path → inspirations |
| GET | `/api/v1/external-inspirations/context` | Proof-layer context preview |
| POST | `/api/v1/external-inspirations/sync` | Re-sync entities + records + ledger (auth) |

## Registered inspirations (v0.1)

| Slug | Entity ID | Source | Contributions |
|------|-----------|--------|---------------|
| `octp` | `pocp-insp-octp` | [openoctp/spec](https://github.com/openoctp/spec) | Provenance, signed integrity, verification claims |
| `garl` | `pocp-insp-garl` | [Garl-Protocol/garl](https://github.com/Garl-Protocol/garl) | Agent receipts |
| `receipt` | `pocp-insp-receipt` | [MorkeethHQ/receipt](https://github.com/MorkeethHQ/receipt) | Receipt hashing |
| `erc-8004` | `pocp-insp-erc-8004` | [erc-8004/erc-8004-contracts](https://github.com/erc-8004/erc-8004-contracts) | Agent feedback + registration |
| `meritocrab` | `pocp-insp-meritocrab` | [hydai/meritocrab](https://github.com/hydai/meritocrab) | Verifiers, audit, review queue, webhooks |
| `contributor-attribution` | `pocp-insp-contributor-attribution` | [drdeeks/contributor-attribution](https://github.com/drdeeks/contributor-attribution) | Code context + Merkle proof |
| `proof-of-contribution` | `pocp-insp-proof-of-contribution` | [dannwaneri/proof-of-contribution](https://github.com/dannwaneri/proof-of-contribution) | Expert cards |
| `trustmygit` | `pocp-insp-trustmygit` | [TrustMyGit/TrustMyGit](https://github.com/TrustMyGit/TrustMyGit) | Git evidence + portable reputation (no token) |
| `clarion-unified` | `pocp-insp-clarion-unified` | PoCP-native | Unified Clarion review packet |
| `chaoss` | `pocp-insp-chaoss` | [chaoss/community](https://github.com/chaoss/community) | Transparency reports |
| `all-contributors` | `pocp-insp-all-contributors` | [all-contributors/all-contributors](https://github.com/all-contributors/all-contributors) | Contributor registries |
| `opensource-guides` | `pocp-insp-opensource-guides` | [github/opensource.guide](https://github.com/github/opensource.guide) | Governance docs |
| `forgefed` | `pocp-insp-forgefed` | [ForgeFed/ForgeFed](https://github.com/ForgeFed/ForgeFed) | Portable federation |

## Evaluating inspirations (protocol mapping)

Detailed borrow / reject / module maps: [inspiration-mappings/README.md](./inspiration-mappings/README.md)

| Slug | Entity ID | Source | Mapping doc |
|------|-----------|--------|-------------|
| `sourcecred` | `pocp-insp-sourcecred` | [sourcecred/sourcecred](https://github.com/sourcecred/sourcecred) | [sourcecred.md](./inspiration-mappings/sourcecred.md) |
| `poc-protocol-core` | `pocp-insp-poc-protocol-core` | [Proof-of-Contribution-Protocol-Core](https://github.com/Gitdigital-products/Proof-of-Contribution-Protocol-Core) | [poc-protocol-core.md](./inspiration-mappings/poc-protocol-core.md) |
| `mcp` | `pocp-insp-mcp` | [modelcontextprotocol/spec](https://github.com/modelcontextprotocol/spec) | [mcp.md](./inspiration-mappings/mcp.md) |

## Benchmark inspirations (round 8 — evaluating)

Distributed AI / compute / agent marketplace benchmarks. See [DISTRIBUTED-INTELLIGENCE-BENCHMARK.md](./DISTRIBUTED-INTELLIGENCE-BENCHMARK.md) · [COMPUTE-ADAPTER-SPEC.md](./COMPUTE-ADAPTER-SPEC.md).

| Slug | Entity ID | Tier | Mapping doc |
|------|-----------|------|-------------|
| `gensyn` | `pocp-insp-gensyn` | AI training network | [gensyn.md](./inspiration-mappings/gensyn.md) |
| `akash` | `pocp-insp-akash` | Compute marketplace | [akash.md](./inspiration-mappings/akash.md) |
| `render-network` | `pocp-insp-render` | GPU network | [akash.md](./inspiration-mappings/akash.md) |
| `io-net` | `pocp-insp-io-net` | GPU network (ML scale) | [ionet.md](./inspiration-mappings/ionet.md) |
| `gitcoin` | `pocp-insp-gitcoin` | Public goods funding | [gitcoin.md](./inspiration-mappings/gitcoin.md) |
| `intelligent-internet` | `pocp-insp-intelligent-internet` | II account/agent | [intelligent-internet.md](./inspiration-mappings/intelligent-internet.md) |
| `singularitynet` | `pocp-insp-singularitynet` | AI services market | [agent-marketplace.md](./inspiration-mappings/agent-marketplace.md) |
| `fetch-ai` | `pocp-insp-fetch-ai` | Agent economy | [agent-marketplace.md](./inspiration-mappings/agent-marketplace.md) |
| `provenancekit` | `pocp-insp-provenancekit` | EAA attribution | [provenancekit.md](./inspiration-mappings/provenancekit.md) |

## Declined benchmarks (recorded)

| Slug | Entity ID | Reason |
|------|-----------|--------|
| `bittensor` | `pocp-insp-bittensor` | Token-miner subnet marketplace |
| `virtuals-protocol` | `pocp-insp-virtuals` | Agent-native token issuance |
| `agent-commons` | `pocp-insp-agent-commons` | Token-first economics |
| `lineage` | `pocp-insp-lineage` | Chain-required royalty settlement |

## Graph edges

Community inspiration entities appear on the contribution graph:

| Relation | Meaning |
|----------|---------|
| `learned_from` | PoCP AI Commons org → external inspiration entity |
| `uses_pattern_from` | Contribution hub → inspiration (when evidence matches borrowed modules) |
| `trusts_peer` | PoCP org → federation peer community entity |
| `federated_with` | Local node → trusted peer |
| `hosts` | PoCP org → local federation node |

## Federation peer community entities

Trusted nodes in `trusted_nodes.yaml` (or `POCP_TRUSTED_NODES`) are mirrored as `community` entities:

| Method | Path |
|--------|------|
| GET | `/api/v1/federation/peers/entities` |

Local node entity id: `pocp-entity-federation-local` · Peer id pattern: `pocp-entity-federation-peer-{node_id}`

## Federated import graph hubs

Each `FederatedImport` record becomes a graph hub node (`federation-import:{id}`):

| Relation | Meaning |
|----------|---------|
| `exported_contribution` | Peer community entity → import hub |
| `imported_to` | Import hub → primary contributor entity |
| `received_import` | Local node → import hub |

| Method | Path |
|--------|------|
| GET | `/api/v1/federation/imports/graph-summary` |
| GET | `/api/v1/federation/entities/{entity_id}/imports` |
| GET | `/api/v1/federation/peers/{node_id}/imports` |

Import source nodes without a trusted_nodes entry still get inferred community entities.

## Proof packet layer

Contribution proof packets include `external_inspirations_context` — which registry inspirations relate to evidence module hints, plus a full registry summary for auditors.

## Startup

On API startup, inspiration **entities** and **records** are synced idempotently (same pattern as genesis entities and code attribution builders).

## Sync script

```bash
curl -X POST http://localhost:8000/api/v1/external-inspirations/sync \
  -H "Authorization: Bearer $POCP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"write_ledger": true}'
```
