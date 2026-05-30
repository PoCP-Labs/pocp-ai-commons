# Code Contribution Registry

PoCP should remember **who built which parts of the codebase**, not only who merged a single GitHub account.

This registry connects:

```text
Path in repository
→ Builder (Human / Agent / LLM)
→ Entity record
→ Attribution DB rows
→ Ledger event
→ Reputation (code_registry category)
```

## Builders (v0.1)

| Slug | Entity | Primary scope | Status |
|------|--------|---------------|--------|
| `proof` | pocp-entity-proof | Proof packets, evidence, ledger chain, export API | inferred — maintainer confirm |
| `poethon` | pocp-entity-poethon | Python backend, models, migrations, core services | inferred — maintainer confirm |
| `pocp-helper` | pocp-entity-pocp-helper | Auth, AI chat, frontend, CI, federation glue | inferred — maintainer confirm |
| `lumen-0` | pocp-entity-lumen-0 | Protocol narrative, genesis docs, Sprint planning | confirmed |
| `desui` | pocp-entity-desui | Validator / witness design | confirmed |
| `clarion-0` | pocp-entity-clarion-0 | Review assistant | confirmed |
| `rain` | pocp-entity-rain | Founder / maintainer; root governance docs + **residual** unassigned paths | confirmed |

**Inferred** means attribution was derived from module analysis and patch history, not from signed git trailers. Maintainers should confirm or correct paths in `backend/config/code_attribution.yaml`.

## Machine-readable registry

Edit:

`backend/config/code_attribution.yaml`

- `builders` — identity, roles, summary  
- `path_rules` — glob/path prefixes per builder  
- `reward_policy` — reputation per file (cap), ledger event type  
- `attribution_policy.residual_builder` — unmapped files count toward Rain (founder)  

## Commands

**Report only** (no DB writes):

```bash
cd backend
python scripts/sync_code_attribution.py --report
```

**Sync** (entities + `code_attribution_records` + ledger):

```bash
python scripts/sync_code_attribution.py --sync
python scripts/sync_code_attribution.py --sync --award-reputation
```

Requires DB (Docker Postgres or SQLite) and migrations applied.

## HTTP API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/code-attribution/registry` | Full YAML registry |
| GET | `/api/v1/code-attribution/report` | Live scan of repository |
| POST | `/api/v1/code-attribution/match` | Match one path to builders |
| GET | `/api/v1/code-attribution/records` | Persisted attribution rows |
| POST | `/api/v1/code-attribution/sync` | Sync + optional reputation + ledger (auth required) |

## Evaluation and rewards

| Step | Mechanism |
|------|-----------|
| **Record** | `code_attribution_records` table + ledger `code_attribution_sync` |
| **Evaluate** | File/line counts per builder; future: PR reviews, test coverage |
| **Reward** | `code_registry` reputation category (configurable cap); full CP/Credits still require human-reviewed Contribution Events |

Code registry reputation is a **Genesis-era bootstrap**. Production should migrate to verified Contribution Events per [CODE-CONTRIBUTION-COMMONS.md](../CODE-CONTRIBUTION-COMMONS.md).

## Future: git-native attribution

1. Require `Co-authored-by: Proof <…>` or `Builder: proof` trailers in commits.  
2. CI parses trailers on merge → append to registry.  
3. Link PR → Contribution Event → same loop as task contributions.  

## Maintainer checklist

- [ ] Confirm or correct `proof`, `poethon`, `pocp-helper` path rules  
- [ ] Run `--report` and resolve `unassigned_*` hotspots  
- [ ] Run `--sync --award-reputation` after major releases  
- [ ] Add new builders to YAML + `genesis.py` + this doc  

## Related

- [CODE-CONTRIBUTION-COMMONS.md](../CODE-CONTRIBUTION-COMMONS.md)  
- [GENESIS-CODE-CONTRIBUTORS.md](../GENESIS-CODE-CONTRIBUTORS.md)  
- [ARCHITECTURE.md](./ARCHITECTURE.md)
