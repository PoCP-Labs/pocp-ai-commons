# Pilot Launch Checklist

Step-by-step checklist to launch a **Three-Layer Entity Network Pilot** on the public internet — validating protocol memory, distributed intelligence, and distributed compute, not only human signups.

Target scale: **≥30 active Entities across ≥4 types** (Human, Agent, Skill, LLM, …) within a 30–100 Entity network envelope.

Part of **Epic B** ([#29](https://github.com/PoCP-Labs/pocp-ai-commons/issues/29)). Prerequisites: **Epic A** ([#31](https://github.com/PoCP-Labs/pocp-ai-commons/issues/31)) — especially A1/A2 green.

See also: [PUBLIC-DEPLOY.md](./PUBLIC-DEPLOY.md) · [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md) · [PILOT-FINALIZER-RECRUIT.md](./PILOT-FINALIZER-RECRUIT.md) · [SPRINT_ALPHA.md](./SPRINT_ALPHA.md) · [PILOT-NEURAL-INTERNET-HANDBOOK.md](./PILOT-NEURAL-INTERNET-HANDBOOK.md) · [DEPLOYMENT-TOPOLOGY-GUIDE.md](./DEPLOYMENT-TOPOLOGY-GUIDE.md) · [NEURAL-INTERNET-MASTER-PLAN.md](./NEURAL-INTERNET-MASTER-PLAN.md)

---

## Phase 0 — Preconditions

- [ ] Epic A smoke test passes on staging: `python backend/scripts/smoke_test.py https://api.staging.example.com`
- [ ] `ENABLE_DEV_LOGIN=false` on public host
- [ ] GitHub OAuth App configured (see [PUBLIC-DEPLOY.md § Step 4](./PUBLIC-DEPLOY.md))
- [ ] HTTPS on both `app.*` and `api.*`
- [ ] PostgreSQL **not** exposed on host port 5432 (`docker-compose.prod.yml`)
- [ ] Strong `POSTGRES_PASSWORD` and `JWT_SECRET` (not repo defaults)
- [ ] Do **not** promise tokens, airdrops, or financial returns

---

## Phase 1 — Infrastructure (1–2 days)

### DNS

| Host | Type | Value |
|------|------|-------|
| `api.your-domain.com` | A | server IP |
| `app.your-domain.com` | A | server IP |

### Config files

```bash
git clone https://github.com/PoCP-Labs/pocp-ai-commons.git
cd pocp-ai-commons
cp deploy/.env.production.example .env
cp backend/.env.production.example backend/.env
```

| File | Must set |
|------|----------|
| `.env` | `POSTGRES_PASSWORD`, `VITE_API_URL=https://api.your-domain.com` |
| `backend/.env` | `BACKEND_URL`, `FRONTEND_URL`, `JWT_SECRET`, `DATABASE_URL`, `GITHUB_*`, `ENABLE_DEV_LOGIN=false` |

### Deploy stack

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose ps
curl -s http://127.0.0.1:8000/health | jq .
```

Validate prod compose without starting:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet
```

### TLS (Caddy recommended)

See [deploy/Caddyfile.example](../deploy/Caddyfile.example) and [PUBLIC-DEPLOY.md § Step 3](./PUBLIC-DEPLOY.md).

- [ ] `curl -s https://api.your-domain.com/health` → `"status": "ok"`
- [ ] Browser opens `https://app.your-domain.com`

---

## Phase 2 — Pilot content (2–5 days)

### Tasks (target: 10–30)

- [ ] Seed templates: `python backend/scripts/seed_pilot_tasks.py --api https://api.your-domain.com` ([config/pilot_tasks.yaml](../backend/config/pilot_tasks.yaml))
- [ ] 3–5 **study / knowledge** tasks (aligned with demo R-notes scenario)
- [ ] 3–5 **open-source / docs** tasks (README, tests, translations)
- [ ] 2–5 **community / volunteer** tasks
- [ ] Each task has clear acceptance criteria and suggested CP / AI Credits
- [ ] Sponsor org (optional) provides API quota or Credits pool

### Finalizers (target: ≥3 distinct Entity types)

- [ ] Recruit finalizer Entities and witness operators — templates: [PILOT-FINALIZER-RECRUIT.md](./PILOT-FINALIZER-RECRUIT.md)
- [ ] Share [ENTITY-EQUALITY.md](./ENTITY-EQUALITY.md) and optional [HUMAN-REVIEW-GUIDE.md](./HUMAN-REVIEW-GUIDE.md)
- [ ] Self-approval blocked in API; default path is policy auto-finalize

### Entity onboarding (not human-only)

- [ ] Share [PILOT-ONBOARDING.md](./PILOT-ONBOARDING.md) (English; StudyAgent path B)
- [ ] **Human Entities:** GitHub Login → wallet → task → submit evidence → review
- [ ] **Agent / Skill Entities:** import or use bundled capabilities; StudyAgent path with `submit_contribution: true`
- [ ] **LLM Witness Entities:** enable Ollama and/or peer witness (`ENABLE_PEER_COMPUTE`, [DISTRIBUTED-LAYERS.md](./DISTRIBUTED-LAYERS.md))
- [ ] Link to [PUBLIC-DEMO.md](./PUBLIC-DEMO.md)
- [ ] Clarify: **AI witnesses advise; policy + quorum finalize traceably** ([ENTITY-EQUALITY.md](./ENTITY-EQUALITY.md))

Verify StudyAgent loop on staging:

```bash
python backend/scripts/study_agent_loop_test.py https://api.staging.example.com
```

---

## Phase 3 — Pilot run (4–8 weeks)

### Target scale — three layers

```text
Protocol layer:
  ≥30 active Entities (≥4 types)
  50–200 approved contribution events
  ≥50 exportable Proof Packets
  ≥1 federation import (when Epic D second node ready)

Distributed intelligence layer:
  ≥30 InvocationTrace records
  avg chain depth ≥3 (Human→Agent→Skill→LLM)
  multi-witness auto-verify on most submissions

Distributed compute layer:
  ≥2 witness compute providers (local Ollama + peer or vLLM)
  GET /api/v1/intelligence/compute/status shows live adapters

Accountability / finalization diversity:
  ≥3 distinct finalizer Entities (any type — Human, Agent, LLM, …)
```

### Weekly metrics

| Metric | How to measure |
|--------|----------------|
| Active Entities | Entities in ≥1 approved/submitted event in 7 days; by `entity_type` |
| Entity type diversity | Distinct types per week; avg types per contribution |
| Return rate | Entities with 2+ contribution-related events in 7 days |
| Contributions submitted | ContributionEvent count by week |
| Proof packets | `GET /contributions/{id}/proof` export count; or approved count via `pilot_metrics.py` |
| Pilot dashboard | `python backend/scripts/pilot_metrics.py https://api.your-domain.com` (or `--db` locally) |
| Invocation depth | `invocation_traces` chain length (StudyAgent path) |
| Witness coverage | auto-verify consensus providers (local + peer + API) |
| Approval rate | approved / submitted |
| AI Credits burn | AIUsageLog sum |
| Abuse flags | 429 limits, rejected evidence, self-approval attempts |

### Anti-abuse spot checks

- [ ] Submit without evidence → 400
- [ ] Contributor tries to approve own contribution → blocked
- [ ] Daily contribution / burn limits behave as configured

Run unit tests locally:

```bash
cd backend && python -m unittest discover -s tests -p "test_*.py"
```

Pilot metrics (three-layer Entity Network dashboard):

```bash
# Against running API (staging / production)
python backend/scripts/pilot_metrics.py https://api.your-domain.com

# Direct database (operator workstation with DATABASE_URL)
cd backend && python scripts/pilot_metrics.py --db

# JSON for dashboards / CI artifacts
python backend/scripts/pilot_metrics.py http://127.0.0.1:8000 --json

# Exit non-zero until all pilot targets met
python backend/scripts/pilot_metrics.py http://127.0.0.1:8000 --strict
```

---

## Phase 4 — Retrospective & Epic D

- [ ] Survey: fairness of CP and AI Credits
- [ ] Reviewer feedback: is multi-witness verification useful?
- [ ] Three-layer check: `python backend/scripts/pilot_metrics.py https://api.your-domain.com`
- [ ] Decision: scale Epic C (graph) / Epic D (second node) / adjust rules
- [ ] Publish short retrospective issue on GitHub (no token promises)

### Epic D — second node (when `federation_imports` is 0)

If pilot metrics shows `federation imports: 0 / 1`, stand up an independent operator node:

- [ ] [deploy/FEDERATION-SECOND-NODE.md](../deploy/FEDERATION-SECOND-NODE.md)
- [ ] [docs/FEDERATION-OPERATOR-RUNBOOK.md](./FEDERATION-OPERATOR-RUNBOOK.md)
- [ ] [docs/FEDERATION-DEMO-TROUBLESHOOTING.md](./FEDERATION-DEMO-TROUBLESHOOTING.md) — if `docker compose -f docker-compose.federation.yml` fails
- [ ] Import one signed proof: `POST /api/v1/federation/import-proof`
- [ ] Re-run pilot metrics — on **mirror/importing node**, `federation_imports` should be ≥ 1 (source nodes may show 0)

---

## Smoke test on production

**Note:** Default smoke test uses **dev-login**. For production with `ENABLE_DEV_LOGIN=false`:

1. Temporarily enable dev-login on a **staging** clone, or
2. Test manually via GitHub Login + UI, or
3. Extend smoke test with a GitHub test account (future work)

---

## Blockers requiring real infrastructure

| Item | Blocked without |
|------|-----------------|
| HTTPS public URL | VPS + domain |
| GitHub OAuth production | OAuth App + matching callback URLs |
| ≥30 active Entities | Community + capability imports + agent paths |
| Second federation node | Second operator + VPS (Epic D) |
| Peer witness compute | `ENABLE_PEER_COMPUTE` + trusted peer URL |

---

## Related GitHub issues

| Epic | Issue |
|------|-------|
| A — Stable stack | [#31](https://github.com/PoCP-Labs/pocp-ai-commons/issues/31) |
| B — Pilot | [#29](https://github.com/PoCP-Labs/pocp-ai-commons/issues/29) |
| C — Contribution graph | [#26](https://github.com/PoCP-Labs/pocp-ai-commons/issues/26) |
