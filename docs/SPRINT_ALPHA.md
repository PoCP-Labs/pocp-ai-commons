# PoCP AI Commons — Sprint Alpha Patch

## Goal

Turn the Genesis demo into a real usable MVP:

```text
Login → Human Entity → Wallet → AI Chat burns Credits → Contribution → AI Verify → Human Review → CP/Credits → Ledger
```

## What this patch adds

- GitHub OAuth and local dev login
- `UserAccount` linked to Human Entity
- automatic Wallet creation and 100 starter AI Credits
- AI Chat endpoint that burns AI Credits
- AI usage logs
- verifier adapter architecture
- OpenAI verifier
- DeepSeek verifier
- Mock verifier fallback
- multi-verifier consensus endpoint
- minimal anti-abuse helpers

## New endpoints

```text
GET  /api/v1/auth/github/login
GET  /api/v1/auth/github/callback
POST /api/v1/auth/dev-login
GET  /api/v1/me
POST /api/v1/ai/chat
GET  /api/v1/ai/usage
POST /api/v1/contributions/{contribution_id}/auto-verify
```

## Local test flow

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Dev login:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/dev-login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice-dev","email":"alice@example.com"}'
```

Copy the token, then:

```bash
curl http://127.0.0.1:8000/api/v1/me \
  -H "Authorization: Bearer <TOKEN>"
```

AI Chat:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/ai/chat \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"message":"Explain R vectors and matrices simply.","provider":"mock"}'
```

## Guardrails

Do not add token, DAO, blockchain, or payment logic in Sprint Alpha.
