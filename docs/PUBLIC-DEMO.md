# Public Demo Guide

How to demonstrate PoCP AI Commons: **contribution → verification → AI Credits → AI use**.

## Demo script (5 minutes)

### 1. Start the stack

```bash
docker compose up --build
# Or local: see LOCAL-SETUP.md
```

Open http://localhost:3000

### 2. Login

- Click **Dev Login** (or GitHub Login if OAuth configured)
- Show wallet: 100 AI Credits, 0 CP

### 3. AI Chat

- Go to **AI Node** tab
- Send a message (5 Credits burned)
- Show remaining credits and usage history

### 4. Contribution loop

- Go to **Contribute** tab
- Run workflow: Invoke → Submit → AI Witness Review → Human Final Approval
- Note: approval requires a **second** dev-login session as reviewer (not creator)

### 5. Network view

- **Network** tab: entities, latest contribution block, ledger hash
- **Graph** tab: Human → Agent → Skill → LLM chain

## Key talking points

1. **Not a token project** — AI Credits are usage rights from verified contribution
2. **Entity-centric** — Humans, Agents, Skills participate together
3. **AI witness, policy final** — Verifiers advise; witness quorum + entity delegate finalize traceably
4. **Contribution OS** — Ledger, proof packets, graph as protocol primitives

## One-line pitch

> Earn AI access through verified contribution.

## Troubleshooting

- API down → check http://localhost:8000/health
- Self-approval error → use second account as reviewer
- See [LOCAL-SETUP.md](./LOCAL-SETUP.md)
