# LLM language handling (Cursor-style, not UI i18n)

PoCP separates **how humans talk to agents** from **what gets stored on the protocol**.

| Surface | Cursor-like? | Canonical language |
|---------|--------------|-------------------|
| AI Chat, Agent Studio handoffs, coaching | **Yes** — mirror user language | N/A (ephemeral) |
| Witness / verifier JSON, ledger, API `detail` | **No** — structured English fields | English |
| Genesis / protocol docs | Human translations in `docs/genesis/` | English (`GENESIS.md`) |

UI locale packs (`frontend/src/i18n/`) are optional chrome only — **not** this document.

---

## How Cursor does it (no separate “language engine”)

```text
User message (any language)
        │
        ▼
┌───────────────────┐
│ System + rules    │  ← product policy (e.g. follow user language)
│ + conversation    │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Multilingual LLM  │  ← inference; implicit detect + generate
└─────────┬─────────┘
          ▼
    Assistant reply (usually same language as user)
```

There is typically **no** standalone detect→translate pipeline in the chat path:

1. **Detection** — the model infers language from tokens (statistics + training).
2. **Conversion** — the model **generates** the reply in the target language (not a deterministic MT API).
3. **Policy** — `.cursor/rules`, Skills, and system prompts steer *when* to use English vs mirror the user.

PoCP should copy this pattern for **conversational** capabilities, not for ledger or proof bytes.

---

## PoCP mapping

| Component | File | Cursor-style behavior |
|-----------|------|------------------------|
| AI Chat | `services/ai_chat.py` | System prompt includes `llm_language` mirror policy |
| Agent handoffs | `services/agent_studio/cursor_bridge.py` | Handoff prompt: work in user/handoff language, English for code comments unless asked |
| Meta agents | `agents/prompts/_global.md` | Global language rule |
| Witness / auto-verify | `verifiers/openai_verifier.py`, `multi_verifier.py`, `crewai_witness.py` | `verifier_system_prompt()` + `language_hint` on consensus; JSON keys English, rationale/concerns mirror contributor language |
| Clarion packet | `services/clarion.py` | Heuristic packet includes `language_hint`; no extra LLM call |
| Finalize / ledger | `finalization` | Status enums + API `detail` stay English canonical |
| Optional audit | `services/llm_language.py` | `detect_language_hint()` for logs only — not routing |

---

## Implementation pattern

### 1. System prompt (mirror user — like Cursor chat)

```python
from services.llm_language import conversational_system_prompt

system = conversational_system_prompt(
    base="You are PoCP AI Commons assistant…",
    domain="ai_chat",
)
```

Default instruction (see `llm_language.py`):

- Reply in the **same language** as the latest user message unless they ask otherwise.
- Code identifiers, paths, and protocol IDs stay as in the repo (usually English).
- When emitting **protocol JSON** (contribution, proof), use English keys and English canonical values.

### 2. Do not auto-translate protocol writes

Wrong:

```text
User (zh) → MT API → store Chinese-only task.title in Postgres
```

Right:

```text
User (zh) → agent understands zh → drafts English title for API + optional title_zh in metadata
```

### 3. Witness / auto-verify

All LLM witnesses share:

- **System:** `verifier_system_prompt()` in `services/llm_language.py`
- **User:** `build_verifier_prompt(context)` embeds task/contribution JSON + `language_hint`
- **Response:** `POST /api/v1/contributions/{id}/auto-verify` returns `consensus.language_hint`

```bash
# Contributor writes Chinese description → witnesses may return Chinese rationale in JSON
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8008/api/v1/contributions/{id}/auto-verify
```

### 4. Agent Studio → Cursor SDK

`build_handoff_prompt` already sends English playbook excerpts; the **Cursor agent** still mirrors the operator’s language in chat because the **hosted model** does, same as IDE Chat.

No change to Cursor’s SDK is required — only PoCP-side prompt lines.

### 4. Optional: language hint in invocation trace

For observability (not routing):

```python
hint = detect_language_hint(user_message)  # "zh" | "en" | "mixed" | "unknown"
# store in InvocationTrace.metadata_["language_hint"]
```

Use **langdetect** or fast heuristics; never block requests on detection failure.

---

## Environment knobs

| Variable | Purpose |
|----------|---------|
| `POCP_LLM_MIRROR_USER_LANGUAGE` | `true` (default) — append mirror policy to conversational system prompts |
| `POCP_LLM_REPLY_LOCALE` | Force `en` or `zh` for all chat replies (overrides mirror; staging/debug) |
| `POCP_LLM_DETECT_LANGUAGE` | `true` — log `language_hint` on AI usage rows |

---

## What not to build

- A platform-wide “Google Translate service” for chat (unless a dedicated **translation** capability with receipts).
- Chinese-only API `detail` errors (breaks federation and audit).
- Assuming `Accept-Language` controls agent reasoning (HTTP header is for **display** APIs only).

---

## Related

- [LANGUAGE-POLICY.md](./LANGUAGE-POLICY.md) — English canonical on protocol
- [I18N-GUIDE.md](./I18N-GUIDE.md) — UI/API display locales (separate concern)
- [agents/prompts/_global.md](../agents/prompts/_global.md) — Meta agent rules
