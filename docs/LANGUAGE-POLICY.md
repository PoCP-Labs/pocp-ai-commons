# Language Policy — English First

PoCP AI Commons uses **English as the primary language** for the running platform, APIs, UI, operator docs, and canonical protocol text.

## Canonical (English)

| Surface | Location |
|---------|----------|
| Genesis manifesto | [GENESIS.md](../GENESIS.md) |
| Protocol spec | [PROTOCOL-SPEC-v0.1.md](../PROTOCOL-SPEC-v0.1.md) |
| Operator / deploy docs | `docs/*.md` (except `docs/genesis/*` translations) |
| Web dashboard | `frontend/src/` — user-visible strings in English |
| API errors & seed descriptions | `backend/` — English by default |
| Pilot task templates | `backend/config/pilot_tasks.yaml` |
| Entity metadata (`genesis_manifesto_primary`) | `GENESIS.md` |

## Translations (secondary)

Community translations live under `docs/genesis/` (e.g. [zh-CN.md](./genesis/zh-CN.md)). They must not override English in:

- API default fields (`principle`, `name`, `north_star`)
- Production UI fallbacks
- Database seed text shown on the public dashboard

Optional `*_zh` fields in JSON responses exist for i18n clients; English fields are authoritative.

**Bilingual UI (en / zh):** see [I18N-GUIDE.md](./I18N-GUIDE.md) — locale switcher, `Accept-Language`, and `GET /api/v1/entities/ontology?locale=zh`.

## Adding copy

1. Write new user-facing text in English first.
2. Add translations via PR under `docs/genesis/` or a future `locales/` pack.
3. Do not use Chinese (or other languages) as the only string in UI or API `detail` messages.

## Dashboard (local)

The dev-login **persona** selector (Rain / Bob / guest) is documented in [LOCAL-SETUP.md](./LOCAL-SETUP.md). Production disables dev-login.

## Related

- [docs/genesis/README.md](./genesis/README.md) — translation index
- [GOOD_FIRST_ISSUES.md](../GOOD_FIRST_ISSUES.md) — translate GENESIS.md
- [PILOT-ONBOARDING.md](./PILOT-ONBOARDING.md) — English pilot guide
