# AI Credits Guide

AI Credits are **usage rights** inside PoCP AI Commons — not a token, not a speculative asset.

## What they are

- A meter for AI Chat and similar AI-powered features
- Earned through verified contribution (after human approval) and registration grants
- Burned when you use AI tools (default: 5 credits per chat message)

## What they are not

- Not tradable cryptocurrency
- Not guaranteed unlimited free AI
- Not issued as a first-class financial product in Sprint Alpha

## Flow

```text
Registration → 100 starter AI Credits (configurable)
AI Chat → burns credits per message
Contribution approved → additional CP + AI Credits issued
Insufficient credits → chat blocked with clear error
```

## Configuration

See `backend/config/pocp_rewards.yaml` and env vars in `.env.example`:

- `STARTER_AI_CREDITS` (default 100)
- `AI_CHAT_COST_PER_MESSAGE` (default 5)
- `DAILY_AI_CREDITS_BURN_LIMIT` (anti-abuse)

## API

- `POST /api/v1/ai/chat` — burns credits, returns `remaining_credits`
- `GET /api/v1/ai/usage` — usage history for authenticated user

## Ledger

Credit burns and grants are recorded in the ledger and wallet transaction history.

PoCP begins with contribution — not speculation.
