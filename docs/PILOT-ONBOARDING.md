# Pilot Participant Onboarding — Epic B

**Entity Network Pilot:** validate the protocol layer, distributed intelligence layer, and distributed compute layer — not human signup count alone.

**Goal:** ≥30 active Entities (across Human / Agent / Skill / LLM and more), 50–200 approved contribution events, exportable Proof Packets, InvocationTrace depth ≥3.

See also: [INTELLECTUAL-EQUALITY.md](./INTELLECTUAL-EQUALITY.md) · [DISTRIBUTED-LAYERS.md](./DISTRIBUTED-LAYERS.md) · [PILOT-LAUNCH-CHECKLIST.md](./PILOT-LAUNCH-CHECKLIST.md) · [PUBLIC-DEMO.md](./PUBLIC-DEMO.md) · [HUMAN-REVIEW-GUIDE.md](./HUMAN-REVIEW-GUIDE.md) · [LANGUAGE-POLICY.md](./LANGUAGE-POLICY.md)

---

## One sentence

**Everything is an Entity** — earn AI Credits through verified contribution; compute and intelligence run distributed on the network; the protocol remembers the collaboration chain.

- **Network participants:** Human, Agent, Skill, LLM, Tool, Organization — anyone in a contribution event  
- **Traceability:** Every finalization records Entity + policy version in ledger/proof — not a hidden human gate  

---

## How entities join

| Entity type | How to join | Pilot role |
|-------------|-------------|------------|
| **Human** | GitHub OAuth / dev-login | Submit contributions, use AI, optional finalizer |
| **Agent** | manifest import / StudyAgent | Orchestrate tasks, produce InvocationTrace; may finalize per policy |
| **Skill** | AgentSkills import / bundled | Invoked, accumulate reputation |
| **LLM** | Verifier registry (Lumen-0, DeSui, Ollama) | Witness, score (advisory); may finalize per policy |
| **Organization** | Create sponsor org | Publish tasks, sponsor credit pools |

---

## Path A — Human-initiated (classic flow)

1. **Sign in** — GitHub OAuth (production) or dev-login (local). Use **Rain** or **Bob** personas in the dashboard dev selector for the seeded demo.
2. **Wallet** — `GET /api/v1/me` → CP and AI Credits
3. **Pick a task** — from the task list
4. **(Optional) AI Chat** — burns Credits; `provider`: `mock` / `openai` / `ollama`
5. **Submit contribution** — `POST /api/v1/contributions` with evidence
6. **AI witness** — `POST .../auto-verify` (multi-verifier consensus)
7. **Policy finalize** — auto-finalize (default) or optional manual `/finalize` → CP / Credits → ledger → graph

**You cannot finalize your own contribution** when policy forbids self-approval — the API rejects it.

---

## Path B — Multi-entity collaboration (StudyAgent, recommended)

Best for study notes / knowledge structuring — one event with **Human + Agent + Skill + LLM** online:

```http
POST /api/v1/intelligence/agents/study/run
Authorization: Bearer <token>

{
  "topic": "R matrix and vector operations",
  "task_id": "<task UUID>",
  "llm_provider": "mock",
  "submit_contribution": true
}
```

```text
Human Entity → StudyAgent → R-Tutor Skill → LLM Witness
         ↓
   InvocationTrace + Contribution Event
         ↓
   auto-verify (distributed witnesses)
         ↓
   Policy finalize (Clarion-0 delegate or auto) → Ledger + Graph
```

**Acceptance check:**

```bash
python backend/scripts/study_agent_loop_test.py http://127.0.0.1:8000
```

**UI:** Capability tab → StudyAgent (NN-3) → select task → Run.

**Export proof:**

```http
GET /api/v1/contributions/{id}/proof
```

---

## Path C — Compute layer (optional, Epic D+)

Community nodes provide witness compute:

```text
ENABLE_OLLAMA_VERIFIER=true
ENABLE_PEER_COMPUTE=true
```

See [DISTRIBUTED-LAYERS.md](./DISTRIBUTED-LAYERS.md) · `GET /api/v1/intelligence/compute/status`

GPU operators participate in the witness pipeline as Entities — **compute contribution is still contribution**.

---

## Reviewer duties (human accountability anchor)

- Read evidence and InvocationTrace
- Use AI witness advice, decide independently
- `reject` / `request-changes` when quality is insufficient

See [HUMAN-REVIEW-GUIDE.md](./HUMAN-REVIEW-GUIDE.md).

---

## Pilot task templates (10–30)

One-command seed (10 built-in templates):

```bash
python backend/scripts/seed_pilot_tasks.py --api http://127.0.0.1:8000
```

Definition file: [backend/config/pilot_tasks.yaml](../backend/config/pilot_tasks.yaml) (English)

| Type | Example | Entities involved |
|------|---------|-------------------|
| Study notes | R matrix notes | Human + StudyAgent + Skill + LLM |
| Documentation | LOCAL-SETUP improvement PR | Human + (optional) Agent |
| Skill maintenance | Import and execute AgentSkill | Human maintainer + Skill |
| Witness compute | Run Ollama peer witness | Human operator + LLM Entity |
| Community | Onboard Reviewer entities | Human + Organization |

---

## FAQ

**Q: Are “users” only humans?**  
No. PoCP network participants are **Entities**. Humans are the accountability anchor, not the only actor. See [INTELLECTUAL-EQUALITY.md](./INTELLECTUAL-EQUALITY.md).

**Q: Where do AI Credits come from?**  
Registration grant + awards after approved contributions.

**Q: Can contributions be exported?**  
`GET /contributions/{id}/proof` — Proof Packet; federation nodes may opt in to import reputation.

**Q: How is this different from ChatGPT?**  
Distributed witnesses + multi-entity collaboration chains + verifiable ledger — intelligence belongs to the network, not a single API.

**Q: How do I read Pilot layer metrics?**  
`python backend/scripts/pilot_metrics.py http://127.0.0.1:8000` (or `--db` / `--json`). See [PILOT-LAUNCH-CHECKLIST.md](./PILOT-LAUNCH-CHECKLIST.md).

---

## Community templates (Chinese)

Chinese community announcement templates for finalizers remain in [PILOT-FINALIZER-RECRUIT.md](./PILOT-FINALIZER-RECRUIT.md) as optional outreach copy. Operator docs and the running platform stay **English-first**.
