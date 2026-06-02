# Runtime Agents — Protocol witnesses (not coders)

**Do not** assign these as Cursor coding agents. Meta agents **invoke** them via verifier/API paths only.

| Name | entity_id | Role |
|------|-----------|------|
| **Lumen-0** | `pocp-entity-lumen-0` | Witness — interpret evidence, advisory scores |
| **DeSui** | `pocp-entity-desui` | Witness — cross-check, challenge claims |
| **Clarion-0** | `pocp-entity-clarion-0` | Delegate — structure evidence, risk notes, finalization **advisory** |

## Language (Cursor-style)

- Read task/contribution evidence in any language; write **rationale** and **concerns** in the contributor’s dominant language when using LLM witnesses.
- JSON keys, scores, and `recommended_status` enums stay **English** — see `docs/LLM-LANGUAGE.md` and `services/llm_language.py`.

## Invariant

Runtime agents **never alone** issue CP, AI Credits, or reputation changes. Policy finalization must record:

- which policy ran
- which delegate/witness participated
- traceable finalizer entity_id

## For Forge-0 / Gauge-0

- Use existing adapters under `backend/services/verifiers/`.
- Tests may mock Runtime responses; do not write ledger rows as if Lumen finalized rights.

## Reference

[GENESIS.md](../../GENESIS.md) · [docs/PROTOCOL.md](../../docs/PROTOCOL.md)
