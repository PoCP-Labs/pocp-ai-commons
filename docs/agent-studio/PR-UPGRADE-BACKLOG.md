# PR Upgrade Backlog — Agent Studio

Maps [UPGRADE-ROADMAP-PR-PLAN.md](../UPGRADE-ROADMAP-PR-PLAN.md) to Meta Agents and handoffs.

**Mission plans:** `phase_a_kernel` (PA-1..6) then `capability_internet` (CI-1..12). PR-01..15 span both.

---

## PR → Agent → Acceptance

| PR | Primary Meta Agent | Support | Acceptance |
|----|-------------------|---------|------------|
| PR-01 | Pipeline-0 | Gauge-0 | `black --check backend` + smoke_test |
| PR-02 | Herald-0 | Compass-0 | docs link script / manual README audit |
| PR-03 | Herald-0 | Atlas-0 | protocol docs present in tree |
| PR-04 | Atlas-0 | — | `pytest test_entity_ontology` — 14+ types |
| PR-05 | Atlas-0 | Grid-0 | `POST /nodes/register`, well-known JSON |
| PR-06 | Pulse-0 | Atlas-0 | registry API + execute receipt |
| PR-07 | Pulse-0 | Vault-0 | invocation schema v0.3 fields |
| PR-08 | Forge-0 | Sentinel-0 | proof + verify endpoints |
| PR-09 | Prism-0 | Vault-0 | approve → settlement → wallet |
| PR-10 | Prism-0 | Lex-0 | wallet units CP/AIC/CC |
| PR-11 | Sentinel-0 | Canvas-0 | graph API scoped edges |
| PR-12 | Vault-0 | Atlas-0 | protocol_events append |
| PR-13 | Mesh-0 | Gauge-0 | MINIMUM-LIVING-NETWORK green |
| PR-14 | Sentinel-0 | Atlas-0 | nonce + signature tests |
| PR-15 | Forge-0 | Herald-0 | sdk stub importable |

---

## Priority order (execution)

```text
Wave 0 (public sync):  PR-01, PR-02, PR-03  — push local to GitHub main
Wave 1 (kernel):       PR-04..PR-07         — overlaps PA-1, PA-2, CI-4..CI-6
Wave 2 (trust/value):  PR-08..PR-10         — overlaps PA-3, CI-8..CI-12
Wave 3 (network demo): PR-11..PR-13         — minimum living network
Wave 4 (scale):        PR-14..PR-15         — security + SDK
```

---

## Blockers from public review

| Blocker | Resolution |
|---------|------------|
| Python 1-line files on raw.githubusercontent | Push formatted local tree; add CI format check |
| README still “AI Credits only” on public | Merge local README + PR-03 docs |
| Open issues scattered | Relabel into Group 1/2/3 above |

---

## Cursor automation

After `py -3.12 -m pip install cursor-sdk`:

```powershell
.\scripts\run-studio-super-loop.ps1
```

First code handoff target: **PR-05 NodeProfile** (Atlas-0) after **PR-01 push** verified on public.
