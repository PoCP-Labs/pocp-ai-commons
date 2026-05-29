# Development Tasks

This file lists current code production tasks for PoCP AI Commons.

These tasks are for Genesis Code Contributors, including developers, issue writers, spec contributors, AI agents, skill builders, testers, reviewers, and documentation contributors.

## Current Sprint Goal

Build and stabilize the first usable PoCP AI Commons loop:

```text
Login
→ AI Credits Wallet
→ AI Chat
→ Contribution Submission
→ AI Verification
→ Human Review
→ CP / AI Credits
→ Ledger
→ Contribution Graph
```

## Backend Tasks

### Auth and Identity

- [ ] Add GitHub OAuth login
- [ ] Add dev login for local testing
- [ ] Add `/api/v1/me`
- [ ] Auto-create Human Entity after login
- [ ] Auto-create Wallet after login
- [ ] Grant starter AI Credits

### AI Credits

- [ ] Add AI usage log model
- [ ] Add AI Chat endpoint
- [ ] Burn AI Credits per chat message
- [ ] Block chat when Credits are insufficient
- [ ] Add CreditTransaction for AI usage
- [ ] Add ledger record for AI Credits burn

### AI Verifier

- [ ] Add BaseVerifier interface
- [ ] Add MockVerifier
- [ ] Add OpenAIVerifier
- [ ] Add DeepSeekVerifier
- [ ] Add MultiVerifierService
- [ ] Add consensus aggregation
- [ ] Store structured verifier result
- [ ] Add fallback when API keys are missing

### Anti-Abuse

- [ ] Require evidence for contribution submission
- [ ] Add daily contribution limit
- [ ] Add daily AI Credits burn limit
- [ ] Keep self-approval blocked
- [ ] Add clear error messages

### Tests

- [ ] Smoke test: login → AI Chat → Credits burn
- [ ] Smoke test: contribution → AI verify → human approve
- [ ] Test insufficient Credits
- [ ] Test missing evidence
- [ ] Test self-approval blocked

## Frontend Tasks

### Login / Profile

- [ ] Add Login panel
- [ ] Add Dev Login button
- [ ] Add GitHub Login button
- [ ] Store token locally for MVP
- [ ] Show current Human Entity
- [ ] Show wallet balance
- [ ] Add Logout

### AI Chat

- [ ] Add AI Chat tab
- [ ] Show cost per message
- [ ] Show remaining AI Credits
- [ ] Show insufficient Credits error
- [ ] Show latest response
- [ ] Show usage history if API supports it

### Contribution Flow

- [ ] Improve contribution form
- [ ] Require evidence field
- [ ] Show AI verification status
- [ ] Show human review status
- [ ] Show awarded CP and Credits

### Contribution Graph

- [ ] Improve graph visualization
- [ ] Add node types:
  - Human
  - Agent
  - Skill
  - Contribution
  - AI Verifier
  - Human Reviewer
  - Ledger
- [ ] Add Entity detail view
- [ ] Add Skill detail view

## Documentation Tasks

- [ ] Write `LOCAL-SETUP.md`
- [ ] Write `API-SPEC.md`
- [ ] Write `ARCHITECTURE.md`
- [ ] Write Verifier Adapter Guide
- [ ] Write AI Credits Guide
- [ ] Write Human Review Guide
- [ ] Write Code Contribution Commons guide

## Skill Tasks

- [ ] Define Study Helper Skill
- [ ] Define Code Review Skill
- [ ] Define Translation Skill
- [ ] Define Resume Helper Skill
- [ ] Define Research Summary Skill

## Review Tasks

- [ ] Review Sprint Alpha patch
- [ ] Review verifier prompts
- [ ] Review AI Chat Credits burn logic
- [ ] Review contribution graph data model
- [ ] Review anti-abuse rules

## Labels to use

```text
backend
frontend
ai-verifier
ai-credits
contribution-graph
skill
testing
documentation
good first contribution
help wanted
anti-abuse
review
```

PoCP begins with contribution.
