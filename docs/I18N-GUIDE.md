# Internationalization (i18n) — English + Chinese

PoCP follows [LANGUAGE-POLICY.md](./LANGUAGE-POLICY.md): **English is canonical** for API defaults, ledger text, and protocol specs. **Chinese (`zh`)** is a first-class display locale for the dashboard and ontology APIs.

This is **not** the same as Cursor’s chat language detection — PoCP uses explicit locale negotiation and translation packs.

---

## Architecture

```text
Browser
  ├─ detect: navigator.language → localStorage pocp_locale → ?lang=zh
  ├─ UI: frontend/src/i18n/locales/{en,zh}.json
  └─ API: Accept-Language: zh-CN,zh;q=0.9 on every fetch

Backend
  ├─ services/i18n.py — parse locale, pick *_zh fields
  ├─ GET /api/v1/locale — supported locales + effective locale
  └─ GET /api/v1/entities/ontology?locale=zh — localized labels
```

| Layer | English canonical | Chinese display |
|-------|-------------------|-----------------|
| UI chrome | `locales/en.json` | `locales/zh.json` |
| Entity ontology API | `label`, `description` | `label_zh` → `label` when `locale=zh` |
| Intelligence / protocol | `principle`, `name` | `principle_zh`, `name_zh` (same pattern) |
| User-generated content | Stored as submitted | No auto-translate in MVP |

---

## Frontend

### Auto-detect on first visit

1. URL `?lang=zh` or `?locale=zh` (saved to `localStorage`)
2. Else `localStorage.pocp_locale`
3. Else `navigator.language` starts with `zh` → `zh`, else `en`

### Manual switch

Header **language dropdown** (`LocaleSwitcher`) sets `pocp_locale` and reloads copy via `useI18n().t(key)`.

### Add UI strings

1. Add key to `frontend/src/i18n/locales/en.json`
2. Add Chinese to `zh.json`
3. In component: `const { t } = useI18n();` then `t("my.key")`

### API fields with `*_zh`

```javascript
import { pickLocalized } from "./i18n/index.jsx";
const label = pickLocalized(typeSpec, "label", locale);
```

`fetchJson` already sends `Accept-Language` from the active UI locale.

---

## Backend

### Negotiation

| Input | Precedence |
|-------|------------|
| `?locale=zh` | Highest |
| `Accept-Language: zh-CN,...` | Second |
| Default | `en` |

```python
from services.i18n import locale_from_request, pick_localized, ontology_document_for_locale
```

### Endpoints

| Endpoint | Behavior |
|----------|----------|
| `GET /api/v1/locale` | Lists `en`, `zh` and resolved locale |
| `GET /api/v1/entities/ontology?locale=zh` | Localized type/role labels |
| `GET /api/v1/locale/preview-ontology` | Smoke view of localization |

### Add bilingual API fields

1. Keep English field as source of truth (`name`, `description`, …)
2. Add `name_zh`, `description_zh` in the same dict
3. In router, call `locale_from_request(...)` and `pick_localized` or `ontology_document_for_locale`

Do **not** return Chinese-only `detail` errors in production — English `detail` stays authoritative per language policy.

---

## Optional: machine translation (Phase B+)

For **dynamic** user content (task titles, contribution descriptions):

| Approach | Pros | Cons |
|----------|------|------|
| **LLM translate on write** | Good quality | Cost, needs audit trail |
| **Google/DeepL API** | Deterministic | External dependency, API keys |
| **Pre-translate at seed** | Simple for demo | Does not scale |

Recommended: store `description` (en) + optional `description_zh` when author supplies both; auto-translate only behind `POCP_AUTO_TRANSLATE=true` with ledger note.

---

## Testing

```bash
curl -s "http://127.0.0.1:8008/api/v1/entities/ontology?locale=zh" | jq '.principle, .entity_types.human.label'
curl -s -H "Accept-Language: zh-CN" http://127.0.0.1:8008/api/v1/locale
```

Open http://localhost:3000/?lang=zh — UI should switch; ontology fetches use `Accept-Language`.

---

## Related

- [LANGUAGE-POLICY.md](./LANGUAGE-POLICY.md)
- [docs/genesis/zh-CN.md](./genesis/zh-CN.md) — manifesto translation (docs only)
