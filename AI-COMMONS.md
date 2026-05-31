# AI Commons

**The first application of PoCP: a contribution-based AI capability network.**

---

## Definition

**AI Commons** is a shared pool of AI capability — models, tools, agents, skills, and compute — governed by contribution rules instead of capital alone.

**PoCP AI Commons** is the open-source reference implementation of that idea.

It answers one practical question:

> How can people who cannot afford premium AI subscriptions still access powerful AI — and how can those who contribute to the network earn more access over time?

---

## The Problem

Today's AI access model:

```text
Pay → Use → Platform captures value
```

Problems:

| Issue | Effect |
|-------|--------|
| Paywall | Students, volunteers, and builders in low-income regions are excluded |
| Platform lock-in | Users train the network with data; platforms keep the upside |
| No contribution record | Real help (reviews, docs, fixes, teaching) is invisible |
| AI as product only | AI is sold as consumption, not as collaborative infrastructure |
| Unemployment anxiety | Developers fear displacement without a new participation model |

---

## The PoCP Alternative

```text
Contribute → Verify → Earn CP + AI Credits → Use AI → Contribute more
```

**AI Commons** means:

1. **Basic AI for everyone** — a starter allocation of AI Credits on registration.
2. **More AI through contribution** — verified work earns additional credits.
3. **Shared network value** — code, skills, and knowledge contributed to the commons improve tools for all participants.
4. **Human final say** — AI verifies; humans approve.

---

## What Gets Shared

Participants may opt in to sharing:

| Asset | Example | V0.1 |
|-------|---------|------|
| Code | PRs, libraries, fixes | ✅ via GitHub-linked tasks |
| Skills | Reusable prompt/tool units | ✅ |
| Reviews | Code review, content review | ✅ |
| Knowledge | Docs, tutorials, Q&A | ✅ |
| Agent configs | Task assistants | ✅ |
| Datasets | Curated learning sets | reserved |
| Workflows | Multi-step pipelines | reserved |

Sharing is **voluntary, scoped, and revocable**.

PoCP AI Commons is not a scraper. It is an **opt-in contribution network**.

---

## What Contributors Receive

| Right | Description | V0.1 |
|-------|-------------|------|
| **AI Credits** | Usable balance for chat, agents, and tools | ✅ |
| **CP (Contribution Points)** | Non-transferable proof of verified contribution | ✅ |
| **Reputation** | Entity-level score with decay | ✅ |
| **Governance weight** | Future; based on CP + reputation | deferred |
| **Revenue share** | Future; requires funded value pool | deferred |

---

## AI Credits Model

### Issuance

| Source | Amount | Notes |
|--------|--------|-------|
| Registration grant | Fixed starter balance | Anti-sybil rules apply |
| Verified contribution | Task-defined + AI suggestion + human approval | Primary earn path |
| Sponsored pool | External funding | Optional community top-up |

### Usage

AI Credits are consumed by:

* chat with LLM providers;
* agent runs;
* skill invocations;
* future tool APIs.

### Rules

* **Non-transferable** in V0.1
* **Non-purchasable** in V0.1 (no pay-to-win)
* **Capped daily burn** optional anti-abuse
* **Ledger-recorded** every issuance and spend

---

## Verification Pipeline

```text
Submit contribution + evidence
        ↓
AI Advisory Review (structured JSON)
  - task_match (0–1)
  - quality (0–1)
  - evidence_score (0–1)
  - risk_flags[]
  - suggested_cp
  - suggested_credits
  - rationale (text)
        ↓
Policy Finalizer (auto or delegate)
  - approve / reject / request_changes (traceable)
  - override suggested rewards when policy allows
        ↓
Ledger writes:
  - contribution_event (final)
  - cp_issue
  - credit_issue
  - reputation_delta
```

AI **never** auto-approves in V0.1.

---

## Entity Model (V0.1 Focus)

```text
Human ──uses──▶ Agent ──calls──▶ Skill ──invokes──▶ LLM
  │                                      │
  └──────── submits contribution ◀───────┘
```

| Entity | Role in AI Commons |
|--------|-------------------|
| **Human** | Contributor, reviewer, owner |
| **Agent** | Task executor, assistant |
| **Skill** | Reusable capability unit |
| **LLM** | Provider node (not a full citizen in V0.1) |

Example:

> Rain (Human) uses StudyAgent (Agent) powered by R-Tutor-Skill (Skill) to produce R language exercises. AI Verifier advises. Maintainer approves. Rain earns AI Credits; Agent and Skill gain reputation.

---

## Anti-Abuse Principles

1. **Starter credits are small** — enough to try, not enough to farm.
2. **Verification required for large grants** — no self-approval.
3. **Rate limits** — per entity, per day.
4. **Appeal path** — rejected contributors can request human review.
5. **Reputation decay** — prevents permanent aristocracy.
6. **Sybil resistance** — start with invite / maintainer vouch; expand later.

---

## Pilot Scope (Phase 2)

Target: **30–100 early contributors**

| Segment | Example tasks |
|---------|---------------|
| Developers | OSS PRs, code review, bug fixes |
| Students | Study material creation, peer tutoring |
| Creators | Docs, tutorials, translations |
| Volunteers | Community moderation, mentoring |

Success = one closed loop repeated reliably across real users.

---

## What AI Commons Is Not

* Not unlimited free AI
* Not a token launchpad
* Not default training on all public GitHub repos
* Not AI-controlled governance
* Not a replacement for employment law or welfare systems

---

## Relation to PoCP Protocol

```text
PoCP (protocol)
    └── AI Commons (first app)
            └── pocp-ai-commons (this repo)
```

Other apps may follow (education commons, care commons, science commons).

AI Commons is the wedge: **high urgency, clear utility, measurable loop**.

---

## Call to Builders

If you are building with Cursor or any other tool, start here:

1. Read [PROTOCOL-SPEC-v0.1.md](./PROTOCOL-SPEC-v0.1.md)
2. Implement the verification loop
3. Ship one task type end-to-end
4. Invite 10 real users
5. Publish what broke

**Share code into the commons. Earn AI from the commons.**

---

*PoCP AI Commons · AI Commons Concept · V0.1*
