# PoCP Protocol — Entity-Centric V0.1

## Definition

**PoCP (Proof of Contribution Protocol)** is a contribution proof protocol for intelligent entities in the age of AI. It records and verifies contributions from Humans, Agents, LLMs, Skills, Tools, Datasets, Workflows, and Organizations in collaborative tasks, and distributes AI usage rights, reputation, opportunity, and governance eligibility according to contribution rules.

> PoCP is not a human points system — it is a contribution proof protocol where humans and intelligent agents participate together.

**PoCP AI Commons** is an open contribution network for humans and intelligent entities. It allows humans, Agents, LLMs, Skills, tools, datasets, and organizations to participate in tasks, verify contributions, accumulate reputation, and receive AI usage rights and network opportunities according to contribution rules.

## Core Concept: Entity

The first-class object in PoCP is not `user` but **Entity** — any intelligent subject capable of producing, verifying, invoking, composing, or governing contributions.

```
contributor = intelligent entity (not necessarily human)
```

### Entity Types (full vision)

| Type | V0.1 | Description |
|------|------|-------------|
| `human` | ✅ | Students, developers, reviewers, organizers |
| `agent` | ✅ | Task executors, coordinators, verifiers |
| `skill` | ✅ | Reusable callable capability units |
| `llm` | provider only | Reasoning, scoring, generation nodes |
| `tool` | reserved | External APIs and data interfaces |
| `dataset` | reserved | Reusable knowledge assets |
| `workflow` | reserved | Repeatable collaboration paths |
| `organization` | reserved | Communities, schools, DAOs, enterprises |
| `community` | reserved | Local or thematic groups |

### Rights Model

| Right | Suitable for | V0.1 |
|-------|--------------|------|
| **Usage Rights** | Human, Organization | AI Credits |
| **Reputation Rights** | Human, Agent, Skill, Dataset, Workflow, Organization | Reputation scores |
| **Governance Rights** | Human, Organization (via proxy for non-human) | Deferred |

> Non-human entities accumulate reputation and contribution records. Governance rights must be exercised by their human owner, maintainer, or community representative.

## V0.1 Minimal Loop

```
Human creates Skill
  ↓
Human / Agent uses Skill to complete task
  ↓
Submit contribution (multi-entity event)
  ↓
AI Verifier pre-review
  ↓
Human Reviewer confirms
  ↓
Human receives AI Credits
  ↓
Agent / Skill receive Reputation
  ↓
Contribution event enters Ledger
```

## Contribution Graph

PoCP is not just a ledger — it is a graph:

```
Human → uses → Agent
Agent → calls → Skill
Skill → uses → LLM
Human → submits → Contribution
Verifier → reviews → Contribution
Reviewer → approves → Contribution
Contribution → issues → Credits
Contribution → increases → Reputation
```

## Reference Demo: R Language Study Materials

| Entity | Type | Role |
|--------|------|------|
| Alice | Human | Student / contributor |
| StudyAgent | Agent | Assistant organizer |
| R-Tutor Skill | Skill | R knowledge structuring |
| GPT-4o / DeepSeek | LLM Provider | AI verifier |
| Bob | Human | Reviewer |

Outcome example:

- Alice: +20 CP, +80 AI Credits
- R-Tutor Skill: +5 Skill Reputation
- StudyAgent: +3 Agent Reputation
- Ledger records multi-entity contribution event
