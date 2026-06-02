import { getAcceptLanguage } from "./i18n/index.jsx";

export const API = import.meta.env.VITE_API_URL || "http://localhost:8008";

const TOKEN_KEY = "pocp_token";

/** Seeded demo personas (dev-login only). See docs/LOCAL-SETUP.md */
export const DEV_PERSONAS = [
  { id: "rain", labelKey: "persona.rain", username: "rain", email: "rain@example.com" },
  { id: "bob", labelKey: "persona.bob", username: "bob", email: "bob@example.com" },
  { id: "guest", labelKey: "persona.guest", username: null, email: null },
];

export const LOOP_STEP_KEYS = [
  "loop.contribute",
  "loop.verify",
  "loop.cp",
  "loop.aiCredits",
  "loop.aiUse",
  "loop.more",
];

export const VALID_TABS = new Set([
  "dashboard",
  "studio",
  "ecosystem",
  "provider",
  "workflow",
  "verify",
  "account",
  "chat",
  "graph",
  "entities",
]);

export const GENESIS_IDS = new Set(["pocp-entity-lumen-0", "pocp-entity-desui"]);

export const LEDGER_EVENT_LABELS = {
  contribution_approved: "Contribution approved",
  registration_grant: "Starter AI Credits granted",
  ai_credits_burned: "AI Credits used",
  compute_provided: "Compute provided",
  intel_provided: "Capability provided",
  protocol_fee_collected: "Protocol fee collected",
  protocol_tokens_burned: "Protocol tokens burned",
  compute_settlement: "Compute settlement",
  trust_list_updated: "Trusted federation nodes updated",
  federation_import: "Contribution imported from peer node",
};

export function tabFromLocation() {
  const params = new URLSearchParams(window.location.search);
  const t = params.get("tab");
  return t && VALID_TABS.has(t) ? t : "dashboard";
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export async function fetchJson(path, options = {}) {
  const token = getToken();
  const headers = {
    "Accept-Language": getAcceptLanguage(),
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const res = await fetch(`${API}${path}`, { ...options, headers });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchJsonOptional(path, fallback) {
  try {
    return await fetchJson(path);
  } catch {
    return fallback;
  }
}

export async function checkPocpHealth() {
  const res = await fetch(`${API}/health`);
  if (!res.ok) {
    throw new Error(
      `API at ${API} returned HTTP ${res.status} (not PoCP — port may be used by another app).`
    );
  }
  const h = await res.json();
  if (h.service !== "pocp-ai-commons") {
    throw new Error(
      `API at ${API} is not PoCP (got service=${h.service ?? "unknown"}). Use docker compose or port 8008.`
    );
  }
  return h;
}

export function truncateHash(value, len = 12) {
  if (!value || typeof value !== "string") return "—";
  return value.length <= len ? value : `${value.slice(0, len)}…`;
}

export function describeLedgerPayload(eventType, payload) {
  if (!payload || typeof payload !== "object") {
    return [{ label: "Details", value: "No payload recorded." }];
  }

  switch (eventType) {
    case "trust_list_updated":
      return [
        { label: "Summary", value: LEDGER_EVENT_LABELS.trust_list_updated },
        {
          label: "Trusted nodes",
          value:
            payload.node_count === 0
              ? "None configured yet (single-node / Genesis stage)"
              : `${payload.node_count} node(s)`,
        },
        { label: "Config source", value: payload.source || "unknown" },
        { label: "List fingerprint", value: truncateHash(payload.trust_list_hash, 20) },
        ...(payload.previous_hash
          ? [{ label: "Previous list", value: truncateHash(payload.previous_hash, 20) }]
          : []),
      ];
    case "contribution_approved":
      return [
        { label: "Summary", value: LEDGER_EVENT_LABELS.contribution_approved },
        ...(payload.cp != null ? [{ label: "CP awarded", value: String(payload.cp) }] : []),
        ...(payload.ai_credits != null
          ? [{ label: "AI Credits awarded", value: String(payload.ai_credits) }]
          : []),
        ...(payload.contribution_id
          ? [{ label: "Contribution", value: truncateHash(payload.contribution_id, 20) }]
          : []),
      ];
    case "registration_grant":
      return [
        { label: "Summary", value: LEDGER_EVENT_LABELS.registration_grant },
        ...(payload.ai_credits != null
          ? [{ label: "AI Credits", value: String(payload.ai_credits) }]
          : []),
      ];
    case "ai_credits_burned":
      return [
        { label: "Summary", value: LEDGER_EVENT_LABELS.ai_credits_burned },
        ...(payload.amount != null ? [{ label: "Amount", value: String(payload.amount) }] : []),
        ...(payload.balance_after != null
          ? [{ label: "Balance after", value: String(payload.balance_after) }]
          : []),
      ];
    case "federation_import":
      return [
        { label: "Summary", value: LEDGER_EVENT_LABELS.federation_import },
        ...(payload.source_node_id ? [{ label: "From node", value: payload.source_node_id }] : []),
        ...(payload.portable_id ? [{ label: "Contributor", value: payload.portable_id }] : []),
      ];
    default:
      return [{ label: "Event data", value: "See raw record below for audit details." }];
  }
}
