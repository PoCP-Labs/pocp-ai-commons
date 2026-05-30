# Sprint Alpha Plan

## Goal

Sprint Alpha turns the Genesis demo into a usable MVP.

The key test:

> Can a real participant use AI Credits, submit contribution, receive AI advisory verification, pass human review, earn CP and AI Credits, and see the contribution recorded?

## Sprint Alpha Loop

```text
Login / Dev Login
→ Human Entity
→ Wallet
→ Starter AI Credits
→ AI Chat
→ Credits Burn
→ Contribution Submission
→ AI Advisory Verification
→ Human Review
→ CP + AI Credits Issuance
→ Ledger Record
→ Reputation Update
→ Contribution Graph
```

## P0 Features

### 1. Identity Entry

Implement:

- Dev Login
- GitHub OAuth if possible
- `/api/v1/me`
- Human Entity auto-creation
- Wallet auto-creation
- Starter AI Credits

### 2. AI Chat with Credits Burn

Implement:

- `/api/v1/ai/chat`
- AI Credits check
- AI Credits deduction
- AI usage log
- Credit transaction
- Ledger record for Credits burn

### 3. AI Verifier Architecture

Implement:

- BaseVerifier
- MockVerifier
- OpenAI-compatible Verifier
- DeepSeek-compatible Verifier
- MultiVerifierService
- Consensus aggregation

### 4. Human Review

Implement:

- Review endpoint / page
- AI advisory summary display
- Approve / reject / need revision
- Override CP / Credits if needed
- Self-approval blocked

### 5. Minimal Anti-Abuse

Implement:

- Evidence required
- Daily contribution limit
- Daily AI Credits burn limit
- Duplicate evidence warning
- Self-approval blocked

## Sprint Alpha Success Criteria

Sprint Alpha is successful when:

```text
A participant can log in
→ receive AI Credits
→ use AI Chat
→ submit contribution
→ receive AI advisory review
→ pass human review
→ earn CP and AI Credits
→ see ledger record
→ see graph relationship
```

## Suggested 4-week plan

### Week 1: Alignment and setup

- Clean README
- Add Sprint Alpha docs
- Add no-token-first FAQ
- Apply Code Commons docs
- Apply Intelligence Layer docs
- Confirm local demo and smoke test

### Week 2: Identity and AI Credits

- Dev Login
- `/api/v1/me`
- Wallet creation
- Starter AI Credits
- AI Chat endpoint
- Credits burn

### Week 3: Verification and review

- MockVerifier
- OpenAI / DeepSeek adapter
- Consensus aggregator
- Human Review page
- CP / Credits issuance

### Week 4: Graph and contribution workflow

- Contribution Graph UI
- Entity / Skill detail
- Good First Issues
- First external PRs
- Build Session #001

PoCP begins with contribution.
