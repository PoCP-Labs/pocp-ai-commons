# Herald-0 handoff — CIP-P0.1 capability-first lock

**Handoff:** `0f50cef2-bf25-496b-9ebc-aa8aa6c021e8`  
**Agent:** `pocp-agent-herald-0`

## Handoff — Herald-0

- **Scope:** [CIP-P0.1] README + docs/protocol/README capability-first lock: 首屏 loop = quote→invoke→receipt→wallet; contribution = opt-in upgrade.
- **Files:** `README.md`, `docs/CAPABILITY-INTERNET-PROTOCOL.md`, `docs/protocol/README.md`, `agents/patches/herald-0-0f50cef2.md`
- **Tests run:** `pytest -q tests/test_meta_agent_registry.py` (6 passed); `ensure_meta_agents.py`; `health_check.py`; relative markdown link check on edited docs
- **Result:** pass
- **Blockers:** none
- **Skill gaps:** none
- **Next agent:** Compass-0 (review per scope)

## Changes

- README: relabeled Genesis MVP / Development Status / Guiding Principles so contribution paths are explicitly opt-in; engineering goal leads with exchange spine.
- `docs/CAPABILITY-INTERNET-PROTOCOL.md`: locked 首屏 narrative + cross-links to protocol index and README.
- `docs/protocol/README.md`: 首屏锁定 line, CIP overview link, fixed `../../agents/...` mission path.
