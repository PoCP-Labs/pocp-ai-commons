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

**Status:** Sprint Alpha — core loop implemented; contributor onboarding and polish in progress.

## Backend Tasks

### Auth and Identity

- [x] Add GitHub OAuth login (backend routes; requires `GITHUB_CLIENT_ID/SECRET`)
- [x] Add dev login for local testing
- [x] Add `/api/v1/me`
- [x] Auto-create Human Entity after login
- [x] Auto-create Wallet after login
- [x] Grant starter AI Credits

### AI Credits

- [x] Add AI usage log model
- [x] Add AI Chat endpoint
- [x] Burn AI Credits per chat message
- [x] Block chat when Credits are insufficient
- [x] Add CreditTransaction for AI usage
- [x] Add ledger record for AI Credits burn

### AI Verifier

- [x] Add BaseVerifier interface
- [x] Add MockVerifier
- [x] Add OpenAIVerifier
- [x] Add DeepSeekVerifier
- [x] Add MultiVerifierService
- [x] Add consensus aggregation
- [x] Store structured verifier result
- [x] Add fallback when API keys are missing

### Anti-Abuse

- [x] Require evidence for contribution submission
- [x] Add daily contribution limit
- [x] Add daily AI Credits burn limit
- [x] Keep self-approval blocked
- [x] Add clear error messages

### Tests

- [x] Smoke test: login → AI Chat → Credits burn
- [x] Smoke test: contribution → AI verify → human approve
- [x] Test insufficient Credits (unit test)
- [x] Test missing evidence (unit test)
- [x] Test self-approval blocked (in smoke test)

## Frontend Tasks

### Login / Profile

- [x] Add Login panel
- [x] Add Dev Login button
- [x] Add GitHub Login button
- [x] Store token locally for MVP
- [x] Show current Human Entity
- [x] Show wallet balance
- [x] Add Logout

### AI Chat

- [x] Add AI Chat tab
- [x] Show cost per message
- [x] Show remaining AI Credits
- [x] Show insufficient Credits error
- [x] Show latest response
- [x] Show usage history if API supports it

### Contribution Flow

- [x] Improve contribution form
- [x] Require evidence field
- [x] Show AI verification status
- [x] Show human review status (dedicated status panel)
- [x] Show awarded CP and Credits (post-approve summary)

### Contribution Graph

- [x] Improve graph visualization
- [x] Add node types legend (Human, Agent, Skill, LLM, Organization)
- [ ] Add Contribution / Reviewer / Ledger node types in graph API
- [x] Add Entity detail view
- [ ] Add Skill detail view (dedicated page)

## Documentation Tasks

- [x] Write `LOCAL-SETUP.md`
- [x] Write `API-SPEC.md`
- [x] Write `ARCHITECTURE.md`
- [x] Write Verifier Adapter Guide (`docs/VERIFIER-GUIDE.md`)
- [x] Write AI Credits Guide (`docs/AI-CREDITS-GUIDE.md`)
- [x] Write Human Review Guide (`docs/HUMAN-REVIEW-GUIDE.md`)
- [x] Write Code Contribution Commons guide (`CODE-CONTRIBUTION-COMMONS.md`)

## Skill Tasks

- [ ] Define Study Helper Skill
- [ ] Define Code Review Skill
- [ ] Define Translation Skill
- [ ] Define Resume Helper Skill
- [ ] Define Research Summary Skill

## Review Tasks

- [x] Review Sprint Alpha patch
- [ ] Review verifier prompts
- [x] Review AI Chat Credits burn logic
- [ ] Review contribution graph data model
- [ ] Review anti-abuse rules

## Community / P2

- [x] Good First Issues list (`GOOD_FIRST_ISSUES.md`)
- [x] Issue creation script (`scripts/create_good_first_issues.ps1`)
- [x] CI smoke test workflow (`.github/workflows/smoke-test.yml`)
- [x] Public demo guide (`docs/PUBLIC-DEMO.md`)
- [x] Create GitHub Issues on remote (Issues #1–#10 on PoCP-Labs/pocp-ai-commons)
- [ ] Pilot with 30–100 users

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
