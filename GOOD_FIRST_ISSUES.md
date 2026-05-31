# Good First Contributions

Welcome to PoCP AI Commons.

This file lists beginner-friendly contribution ideas for Genesis Contributors.

If you want to help, pick one item from the [open issues](https://github.com/PoCP-Labs/pocp-ai-commons/issues), comment that you want to work on it, and submit a PR.

## Documentation

### 1. Improve README clarity

Make the README easier for a first-time visitor to understand.

Suggested focus:

- What is PoCP AI Commons?
- What is the first loop?
- What is AI Credits?
- What is not included in v0.1?

Labels:

```text
good first contribution
documentation
```

### 2. Improve GENESIS.md translations

Polish or extend translations of [GENESIS.md](./GENESIS.md). Available languages: English (canonical), [中文](docs/genesis/zh-CN.md), [Français](docs/genesis/fr.md), [Deutsch](docs/genesis/de.md), [العربية](docs/genesis/ar.md), [Русский](docs/genesis/ru.md). See [docs/genesis/README.md](docs/genesis/README.md).

Labels:

```text
good first contribution
documentation
translation
```

### 3. Add FAQ: Is PoCP a token project?

Write a short FAQ explaining:

- PoCP does not start with a token.
- AI Credits are usage rights, not speculative assets.
- Contribution comes before financialization.

Labels:

```text
documentation
research
good first contribution
```

### 4. Add architecture diagram

Create a Mermaid diagram showing:

```text
Human → Task → Contribution → AI Verifier → Human Review → CP → AI Credits → Ledger
```

Labels:

```text
documentation
architecture
good first contribution
```

## Backend

### 5. Add OpenAI Verifier tests

Test that OpenAI Verifier:

- Builds correct prompt
- Parses JSON
- Falls back safely when API fails
- Never auto-approves contribution

Labels:

```text
backend
ai-verifier
good first contribution
```

### 6. Add DeepSeek Verifier tests

Same as OpenAI verifier tests, but for DeepSeek-compatible API.

Labels:

```text
backend
ai-verifier
good first contribution
```

### 7. Add AI Credits burn tests

Test that:

- AI Chat consumes credits
- Insufficient credits blocks usage
- Usage log is written
- Credit transaction is created

Labels:

```text
backend
testing
good first contribution
```

### 8. Add anti-abuse test cases

Test:

- Missing evidence is rejected
- Daily contribution limit works
- Self-approval is blocked
- Daily AI burn limit works

Labels:

```text
backend
anti-abuse
testing
```

## Frontend

### 9. Improve AI Chat UI

Improve the AI Chat screen:

- Show current Credits
- Show cost per message
- Show insufficient credits message
- Show usage history

Labels:

```text
frontend
good first contribution
```

### 10. Improve Contribution Graph visualization

Improve how nodes and edges are displayed.

Suggested node types:

- Human
- Agent
- Skill
- Contribution
- AI Verifier
- Policy finalizer (Entity-equal)
- Ledger

Labels:

```text
frontend
graph
good first contribution
```

### 11. Add Entity Profile Page

Create a page that shows:

- Entity type
- Wallet
- Reputation
- Contributions
- Ledger records
- Related Agents / Skills

Labels:

```text
frontend
entity
good first contribution
```

## Skills

### 12. Create Study Helper Skill

Define a reusable Skill for learning support.

It should include:

- Name
- Purpose
- Prompt template
- Example input
- Example output
- Safety notes
- Contribution use cases

Labels:

```text
skill
good first contribution
```

### 13. Create Code Review Skill

Define a reusable Skill for code review tasks.

Labels:

```text
skill
ai-verifier
good first contribution
```

### 14. Create Resume Helper Skill

Define a reusable Skill for resume improvement.

Labels:

```text
skill
good first contribution
```

### 15. Create Translation Skill

Define a reusable Skill for translation and localization.

Labels:

```text
skill
translation
good first contribution
```

## Research

### 16. Design CP to AI Credits rule

Propose a simple conversion rule.

Questions:

- Should CP and Credits be 1:1?
- Should high-quality contribution get bonus Credits?
- Should Credits expire?
- How to prevent farming?

Labels:

```text
research
governance
ai-credits
```

### 17. Design Skill Reputation framework

Define how a Skill earns reputation.

Possible signals:

- Invocation count
- Human rating
- Contribution success rate
- Reviewer approval rate
- Risk events

Labels:

```text
research
skill
reputation
```

### 18. Design Agent Reputation framework

Define how an Agent earns reputation.

Labels:

```text
research
agent
reputation
```

### 19. Design Human Review principles

Write reviewer guidelines:

- Fairness
- Evidence
- Conflict of interest
- AI as advisory only
- Appeal process

Labels:

```text
research
human-review
governance
```

## Community

### 20. Create Genesis Build Session plan

Create a plan for the first community build session.

Include:

- 30 min intro
- Demo
- Good First Issues
- Task claiming
- Follow-up

Labels:

```text
community
good first contribution
```

PoCP begins with contribution.
