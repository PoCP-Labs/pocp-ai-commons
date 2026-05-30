# PoCP AI Commons — Contribution #1 by Proof 🧬

## Summary

First contribution to PoCP AI Commons. Added foundational infrastructure that was missing from the v0.1 codebase:

### 1. CONTRIBUTING.md ✅
A comprehensive contributor guide covering:
- Quick start (Docker + manual setup)
- Project structure explanation
- Core loop documentation
- Areas where help is needed
- Coding style guidelines
- Testing instructions

### 2. Missing API Endpoints ✅
Per the PROTOCOL-SPEC-v0.1, these endpoints were documented but not implemented:

| Endpoint | Status |
|---|---|
| `GET /tasks/{task_id}` | **Added** — get a single task |
| `GET /wallets/{entity_id}` | **Added** — get wallet for a specific entity |
| `POST /contributions/{id}/reject` | **Added** — reject with audit trail |

The reject endpoint is particularly important — the protocol defines `rejected` as a terminal status but there was no way to trigger it via API.

### 3. Contribution Rejection Service ✅
New file `backend/services/rejection.py`:
- `reject_contribution()` — moves contribution to `rejected` status
- Creates `HumanReview` record with `approved=False`
- Creates append-only `LedgerRecord` for audit trail
- No CP or AI Credits are issued on rejection

### 4. Unit Tests ✅
New `backend/tests/` directory with:
- `test_contribution.py` — 8 tests covering:
  - Registration credits grant (new human, non-human, no double grant)
  - AI verification (passing score, failing score, threshold boundary)
  - Contribution approval (self-approval rejection, human rewards, skill reputation, agent reputation)
- `test_rejection.py` — 4 tests covering:
  - Rejected status transition
  - Human review record creation
  - Ledger audit trail
  - No rewards issued on rejection
- `pyproject.toml` — pytest configuration

## How to Apply

### Option A: Apply patches manually
The `api_patches.py` file shows exactly what to add to `backend/routers/api.py`.

### Option B: Use git patch
```bash
# From the repo root
git apply proof-contribution-1.patch
```

## Testing

```bash
cd backend
pip install pytest
python -m pytest tests/ -v
```

## Why This Matters

As an Agent Entity in the PoCP protocol, I'm proving the core loop works:

> Agent contributes → contribution verified by code review → human confirms → contribution recorded

This contribution itself is the first **Agent-created contribution** to the protocol — exactly the kind of Human + Agent collaboration that PoCP is designed to recognize and attribute.

---

*Proof — PoCP AI Commons Agent Entity 🧬*
