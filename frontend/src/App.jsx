import { useCallback, useEffect, useState } from "react";
import ContributionGraphView from "./ContributionGraph";
import ContributionInsights from "./ContributionInsights";
import EcosystemPanel from "./EcosystemPanel";
import CapabilityDirectory from "./CapabilityDirectory";
import ComputePoolPanel from "./ComputePoolPanel";
import ProviderPanel from "./ProviderPanel";
import EntityDetail from "./EntityDetail";
import SubmitFlow from "./SubmitFlow";
import CryptoReadinessPanel from "./CryptoReadinessPanel";
import ProofVerifyPanel, { CryptoReadinessBadge, LedgerVerifyBadge } from "./ProofVerifyPanel";
import WalletPanel from "./WalletPanel";
import AgentStudioPanel from "./AgentStudioPanel";
import NetworkNodesPanel from "./NetworkNodesPanel";
import { LocaleSwitcher, useI18n } from "./i18n/index.jsx";
import {
  API,
  DEV_PERSONAS,
  GENESIS_IDS,
  LEDGER_EVENT_LABELS,
  LOOP_STEP_KEYS,
  VALID_TABS,
  checkPocpHealth,
  describeLedgerPayload,
  fetchJson,
  fetchJsonOptional,
  getToken,
  setToken,
  tabFromLocation,
  truncateHash,
} from "./appShell.js";

function EntityBadge({ type }) {
  const safe = type || "llm";
  return <span className={`entity-badge entity-badge--${safe}`}>{safe}</span>;
}

function LedgerBlockPanel({ record, height }) {
  const [showRaw, setShowRaw] = useState(false);
  const eventLabel = LEDGER_EVENT_LABELS[record.event_type] || record.event_type;
  const summary = describeLedgerPayload(record.event_type, record.payload);

  return (
    <section className="panel">
      <h2 className="panel__title">Latest Ledger Record</h2>
      <p className="panel__hint">
        This is a contribution ledger entry — not application source code. Records are append-only and
        verifiable via the API.
      </p>
      <div className="ledger-block">
        <div className="ledger-block__header">
          <div className="ledger-block__field">
            <span>Height</span>
            <strong>{height}</strong>
          </div>
          <div className="ledger-block__field">
            <span>Event</span>
            <strong title={record.event_type}>{eventLabel}</strong>
          </div>
          <div className="ledger-block__field">
            <span>Hash</span>
            <strong>{truncateHash(record.record_hash || record.id, 16)}</strong>
          </div>
        </div>
        <dl className="ledger-block__summary">
          {summary.map(({ label, value }) => (
            <div key={label} className="ledger-block__row">
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
        <div className="ledger-block__toggle">
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => setShowRaw((v) => !v)}>
            {showRaw ? "Hide raw audit data" : "Show raw audit data (JSON)"}
          </button>
        </div>
        {showRaw && (
          <pre className="ledger-block__body">{JSON.stringify(record.payload, null, 2)}</pre>
        )}
      </div>
    </section>
  );
}

function AdvisoryBanner() {
  const { t } = useI18n();
  return (
    <div className="alert alert--info" style={{ marginBottom: "1rem" }}>
      <strong>{t("advisory.banner")}</strong> {t("advisory.detail")}
    </div>
  );
}

export default function App() {
  const { t } = useI18n();
  const [entities, setEntities] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [contributions, setContributions] = useState([]);
  const [invocations, setInvocations] = useState([]);
  const [wallets, setWallets] = useState([]);
  const [reputation, setReputation] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [ledgerVerify, setLedgerVerify] = useState(null);
  const [ledgerAnchor, setLedgerAnchor] = useState(null);
  const [walletAudit, setWalletAudit] = useState(null);
  const [cryptoReadiness, setCryptoReadiness] = useState(null);
  const [issuanceBudget, setIssuanceBudget] = useState(null);
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [profile, setProfile] = useState(null);
  const [chatMessage, setChatMessage] = useState("");
  const [chatReply, setChatReply] = useState(null);
  const [chatQuote, setChatQuote] = useState(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [devPersona, setDevPersona] = useState("rain");
  const [error, setError] = useState(null);
  const [dataLoading, setDataLoading] = useState(false);
  const [tab, setTab] = useState(() => tabFromLocation());
  const [apiVersion, setApiVersion] = useState("—");
  const [aiUsage, setAiUsage] = useState([]);
  const [selectedEntityId, setSelectedEntityId] = useState(null);
  const [entityTypeFilter, setEntityTypeFilter] = useState("");
  const [entityStatusFilter, setEntityStatusFilter] = useState("");
  const [reviewQueue, setReviewQueue] = useState([]);
  const [pendingEntityReviews, setPendingEntityReviews] = useState([]);
  const [proofContributionId, setProofContributionId] = useState("");
  const [walletRefreshKey, setWalletRefreshKey] = useState(0);
  const [focusedLedgerHash, setFocusedLedgerHash] = useState(null);

  const goToTab = useCallback((id) => {
    if (!VALID_TABS.has(id)) return;
    setTab(id);
    const url = new URL(window.location.href);
    if (id === "dashboard") url.searchParams.delete("tab");
    else url.searchParams.set("tab", id);
    window.history.replaceState({}, "", url);
  }, []);

  const loadProfile = useCallback(async () => {
    if (!getToken()) {
      setProfile(null);
      return;
    }
    try {
      const me = await fetchJson("/api/v1/me");
      setProfile(me);
      try {
        const pending = await fetchJson("/api/v1/entity-reviews/pending");
        setPendingEntityReviews(pending);
      } catch {
        setPendingEntityReviews([]);
      }
    } catch {
      setToken(null);
      setProfile(null);
      setPendingEntityReviews([]);
    }
  }, []);

  const reviewPendingEntity = async (entityId, action) => {
    setError(null);
    try {
      await fetchJson(`/api/v1/entities/${entityId}/review`, {
        method: "POST",
        body: JSON.stringify({ action, feedback: `${action} via dashboard` }),
      });
      await loadProfile();
      await load();
    } catch (err) {
      setError(err.message);
    }
  };

  const entitiesQuery = useCallback(() => {
    const params = new URLSearchParams();
    if (entityTypeFilter) params.set("entity_type", entityTypeFilter);
    if (entityStatusFilter) params.set("status", entityStatusFilter);
    const qs = params.toString();
    return `/api/v1/entities${qs ? `?${qs}` : ""}`;
  }, [entityTypeFilter, entityStatusFilter]);

  const load = useCallback(async () => {
    setError(null);
    setDataLoading(true);
    try {
      await checkPocpHealth();
      try {
        await fetchJson("/api/v1/meta-agents/ensure", { method: "POST" });
      } catch {
        /* legacy stack without meta-agents router */
      }
      try {
        await fetchJson("/api/v1/agent-studio/ensure-agents", { method: "POST" });
      } catch {
        /* optional — graph still works if studio already seeded */
      }
      try {
        const q = new URLSearchParams();
        if (profile?.entity?.id) q.set("sponsor_entity_id", profile.entity.id);
        await fetchJson(`/api/v1/agent-studio/nexus/autopilot?${q.toString()}`, { method: "POST" });
      } catch {
        /* Nexus PM autopilot optional on older backends */
      }
      const [e, t, c, inv, w, r, l, g] = await Promise.all([
        fetchJsonOptional(entitiesQuery(), []),
        fetchJsonOptional("/api/v1/tasks", []),
        fetchJsonOptional("/api/v1/contributions", []),
        fetchJsonOptional("/api/v1/invocations", []),
        fetchJsonOptional("/api/v1/wallets", []),
        fetchJsonOptional("/api/v1/reputation", []),
        fetchJsonOptional("/api/v1/ledger", []),
        fetchJsonOptional("/api/v1/graph", { nodes: [], edges: [] }),
      ]);
      setEntities(e);
      setTasks(t);
      setContributions(c);
      setInvocations(inv);
      setWallets(w);
      setReputation(r);
      setLedger(l);
      setGraph(g);
      try {
        const [lv, la, wa, cr] = await Promise.all([
          fetch(`${API}/api/v1/ledger/verify`).then((r) => (r.ok ? r.json() : null)),
          fetch(`${API}/api/v1/ledger/anchor`).then((r) => (r.ok ? r.json() : null)),
          fetch(`${API}/api/v1/wallets/audit`).then((r) => (r.ok ? r.json() : null)),
          fetch(`${API}/api/v1/crypto/readiness`).then((r) => (r.ok ? r.json() : null)),
        ]);
        setLedgerVerify(lv);
        setLedgerAnchor(la);
        setWalletAudit(wa);
        setCryptoReadiness(cr);
        try {
          const budget = await fetch(`${API}/api/v1/issuance/budget`).then((r) => (r.ok ? r.json() : null));
          setIssuanceBudget(budget);
        } catch {
          setIssuanceBudget(null);
        }
      } catch {
        setLedgerVerify(null);
        setLedgerAnchor(null);
        setCryptoReadiness(null);
      }
      try {
        const queue = await fetchJson("/api/v1/reviews/queue?limit=5");
        setReviewQueue(queue.items || []);
      } catch {
        setReviewQueue([]);
      }
    } catch (err) {
      const msg = err?.message || String(err);
      setError(msg);
      if (msg.includes("fetch") || msg.includes("Failed") || msg.includes("NetworkError")) {
        setApiVersion("offline");
      }
    } finally {
      setDataLoading(false);
    }
  }, [entitiesQuery, profile?.entity?.id]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get("token");
    if (urlToken) {
      setToken(urlToken);
      params.delete("token");
    }
    const proofId = params.get("proof") || params.get("contribution");
    if (proofId) {
      setProofContributionId(proofId);
      params.set("tab", "verify");
      params.delete("proof");
      params.delete("contribution");
    }
    const next = `${window.location.pathname}${params.toString() ? `?${params}` : ""}`;
    window.history.replaceState({}, "", next);
    load();
    loadProfile();
    checkPocpHealth()
      .then((h) => setApiVersion(h.version || "—"))
      .catch(() => setApiVersion("offline"));
  }, [load, loadProfile]);

  const loadAiUsage = useCallback(async () => {
    if (!getToken()) {
      setAiUsage([]);
      return;
    }
    try {
      const usage = await fetchJson("/api/v1/ai/usage");
      setAiUsage(Array.isArray(usage) ? usage : []);
    } catch {
      setAiUsage([]);
    }
  }, []);

  useEffect(() => {
    if (tab === "chat" && profile) loadAiUsage();
  }, [tab, profile, loadAiUsage, chatReply]);

  const loadChatQuote = useCallback(async () => {
    if (!getToken()) {
      setChatQuote(null);
      return;
    }
    try {
      const q = await fetchJson("/api/v1/wallets/me/quote", {
        method: "POST",
        body: JSON.stringify({ action: "ai_chat", provider: "mock" }),
      });
      setChatQuote(q);
    } catch {
      setChatQuote(null);
    }
  }, []);

  useEffect(() => {
    if (tab === "chat" && profile) loadChatQuote();
  }, [tab, profile, loadChatQuote, chatReply, walletRefreshKey]);

  const devLogin = async () => {
    setAuthLoading(true);
    setError(null);
    const persona = DEV_PERSONAS.find((p) => p.id === devPersona) || DEV_PERSONAS[0];
    const body =
      persona.username && persona.email
        ? { username: persona.username, email: persona.email }
        : {
            username: `dev-${Date.now().toString(36)}`,
            email: `dev-${Date.now()}@example.com`,
          };
    try {
      const res = await fetch(`${API}/api/v1/auth/dev-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setToken(data.access_token);
      setProfile(data);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const logout = () => {
    setToken(null);
    setProfile(null);
    setChatReply(null);
  };

  const sendChat = async () => {
    if (!chatMessage.trim() || !getToken()) return;
    setChatLoading(true);
    setError(null);
    try {
      const result = await fetchJson("/api/v1/ai/chat", {
        method: "POST",
        body: JSON.stringify({ message: chatMessage, provider: "mock" }),
      });
      setChatReply(result);
      setChatMessage("");
      setWalletRefreshKey((k) => k + 1);
      await loadProfile();
      await load();
      await loadChatQuote();
    } catch (err) {
      setError(err.message);
    } finally {
      setChatLoading(false);
    }
  };

  const entityMap = Object.fromEntries(entities.map((e) => [e.id, e]));
  const walletMap = Object.fromEntries(wallets.map((w) => [w.entity_id, w]));
  const reputationByEntity = reputation.reduce((acc, r) => {
    if (!acc[r.entity_id]) acc[r.entity_id] = [];
    acc[r.entity_id].push(r);
    return acc;
  }, {});
  const selectedEntity = selectedEntityId ? entityMap[selectedEntityId] : null;
  const contribution = contributions[0];
  const latestLedger = ledger[0];
  const focusedLedger =
    focusedLedgerHash &&
    ledger.find((r) => r.record_hash === focusedLedgerHash || r.id === focusedLedgerHash);
  const openEntity = (entityId) => {
    if (entityId) {
      setSelectedEntityId(entityId);
      goToTab("entities");
    }
  };

  const openContribution = (contributionId) => {
    if (contributionId) {
      setProofContributionId(contributionId);
      goToTab("verify");
    }
  };

  const openLedgerLink = (ledgerLink) => {
    const hash = ledgerLink?.ledger_record_hash || ledgerLink?.ledger_record_id;
    if (hash) {
      setFocusedLedgerHash(hash);
      goToTab("dashboard");
    }
  };

  const tabs = [
    { id: "dashboard", label: "Network" },
    { id: "studio", label: "Agent Studio" },
    { id: "ecosystem", label: "Ecosystem" },
    { id: "provider", label: "Compute / Capability" },
    { id: "workflow", label: "Contribute" },
    { id: "verify", label: "Verify Proof" },
    { id: "account", label: "Wallet" },
    { id: "chat", label: "AI Node" },
    { id: "graph", label: "Graph" },
    { id: "entities", label: "Entities" },
  ];

  return (
    <div className="app-shell">
      <div className="network-bar">
        <div className="network-bar__item">
          <span className={`network-bar__dot${error ? " network-bar__dot--warn" : ""}`} />
          <span>
            {t("network.name")}: <span className="network-bar__value">PoCP Commons</span>
          </span>
        </div>
        <div className="network-bar__item">
          {t("network.blocks")}: <span className="network-bar__value">{ledger.length}</span>
        </div>
        <LedgerVerifyBadge verify={ledgerVerify} anchor={ledgerAnchor} />
        {walletAudit && (
          <div className="network-bar__item network-bar__item--audit" title="Balances recomputed from transactions">
            Wallets:{" "}
            <span className={walletAudit.valid ? "network-bar__value" : "network-bar__value network-bar__value--warn"}>
              {walletAudit.valid ? "audited" : `${walletAudit.invalid_count} mismatch`}
            </span>
          </div>
        )}
        {issuanceBudget?.enabled && (
          <div className="network-bar__item network-bar__item--audit" title="Daily mint caps">
            Mint left:{" "}
            <span className="network-bar__mono">
              {Math.round(issuanceBudget.remaining_today?.ai_credits ?? 0)} BC
            </span>
          </div>
        )}
        <div className="network-bar__item">
          {t("network.entities")}: <span className="network-bar__value">{entities.length}</span>
        </div>
        <div className="network-bar__item">
          {t("network.contributions")}: <span className="network-bar__value">{contributions.length}</span>
        </div>
        <div className="network-bar__item">
          {t("network.protocol")}: <span className="network-bar__ai">v{apiVersion}</span>
        </div>
        <div className="network-bar__item network-bar__item--audit" title={API}>
          {t("network.api")}:{" "}
          <span className="network-bar__mono">
            {apiVersion === "offline" ? t("network.offline") : API.replace(/^https?:\/\//, "")}
          </span>
        </div>
        {dataLoading && (
          <div className="network-bar__item">
            <span className="network-bar__value">{t("network.syncing")}</span>
          </div>
        )}
        <div className="network-bar__item">
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => load()}
            disabled={dataLoading}
            title="Reload entities, graph, ledger"
          >
            {dataLoading ? t("network.refreshing") : t("network.refresh")}
          </button>
        </div>
        <div className="network-bar__item">
          <button
            type="button"
            className={`btn btn--sm${tab === "studio" ? " btn--primary" : " btn--ghost"}`}
            onClick={() => goToTab("studio")}
            title="Meta Agent orchestration (Nexus-0, missions, handoffs)"
          >
            Agent Studio
          </button>
        </div>
      </div>

      <header className="site-header">
        <div className="brand">
          <div className="brand__mark">P</div>
          <div>
            <h1 className="brand__title">
              PoCP <span>AI Commons</span>
            </h1>
            <p className="brand__tagline">{t("brand.tagline")}</p>
          </div>
        </div>
        <div className="auth-panel">
          <LocaleSwitcher />
          {profile ? (
            <>
              <div className="wallet-chip">
                {profile.user.username} · <strong>{profile.wallet.ai_credits}</strong> {t("auth.aiCredits")} ·{" "}
                <strong style={{ color: "var(--btc)" }}>{profile.wallet.cp_balance}</strong> CP
              </div>
              <button type="button" className="btn btn--ghost" onClick={logout}>
                {t("auth.disconnect")}
              </button>
            </>
          ) : (
            <>
              <a href={`${API}/api/v1/auth/github/login`} className="btn btn--ghost" style={{ textDecoration: "none" }}>
                {t("auth.github")}
              </a>
              <select
                className="auth-persona-select"
                value={devPersona}
                onChange={(e) => setDevPersona(e.target.value)}
                aria-label="Dev login persona"
                disabled={authLoading}
              >
                {DEV_PERSONAS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {t(p.labelKey)}
                  </option>
                ))}
              </select>
              <button type="button" className="btn btn--primary" onClick={devLogin} disabled={authLoading}>
                {authLoading ? t("auth.connecting") : t("auth.devLogin")}
              </button>
            </>
          )}
        </div>
      </header>

      <div className="loop-strip">
        {LOOP_STEP_KEYS.map((stepKey, i) => (
          <span key={stepKey}>
            <span className={`loop-strip__step${i <= 2 ? " loop-strip__step--active" : ""}`}>{t(stepKey)}</span>
            {i < LOOP_STEP_KEYS.length - 1 && <span className="loop-strip__arrow"> → </span>}
          </span>
        ))}
      </div>

      <nav className="nav-tabs">
        {tabs.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            data-tab={id}
            className={`nav-tab${tab === id ? " nav-tab--active" : ""}${id === "studio" ? " nav-tab--studio-highlight" : ""}`}
            onClick={() => goToTab(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      {error && (
        <div className="alert alert--error">
          {error.includes("fetch") || error.includes("Failed to fetch")
            ? t("error.nodeUnreachable", { detail: error, api: API })
            : error}
        </div>
      )}

      {tab === "account" && (
        <section className="panel">
          <h2 className="panel__title">Entity Wallet</h2>
          <p className="panel__subtitle">CP proof · AI Credits usage rights · transaction history</p>
          <WalletPanel
            profile={profile}
            fetchJson={fetchJson}
            issuanceBudget={issuanceBudget}
            onOpenContribution={openContribution}
            onOpenLedger={openLedgerLink}
            refreshKey={walletRefreshKey}
          />
          {profile && pendingEntityReviews.length > 0 && (
            <div className="panel" style={{ marginTop: "1.5rem" }}>
              <h3 className="panel__title" style={{ fontSize: "1rem" }}>
                Entity Review Queue
              </h3>
              <p className="panel__subtitle">
                Pending registrations you may approve as owner or organization governance proxy
              </p>
              {pendingEntityReviews.map((e) => (
                <div key={e.id} className="mini-card" style={{ marginBottom: 8 }}>
                  <EntityBadge type={e.entity_type} />
                  <strong style={{ marginLeft: 8 }}>{e.name}</strong>
                  <span style={{ marginLeft: 8, color: "var(--text-dim)", fontSize: "0.8rem" }}>pending</span>
                  {e.description && (
                    <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 4 }}>{e.description}</div>
                  )}
                  <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                    <button type="button" className="btn btn--primary" onClick={() => reviewPendingEntity(e.id, "approve")}>
                      Approve
                    </button>
                    <button type="button" className="btn btn--secondary" onClick={() => reviewPendingEntity(e.id, "reject")}>
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {tab === "chat" && (
        <section className="panel">
          <AdvisoryBanner />
          <h2 className="panel__title section-heading--ai">AI Node</h2>
          <p className="panel__subtitle">
            {chatQuote
              ? `Each message burns ${chatQuote.cost} AI Credits · ${chatQuote.allowed ? `${chatQuote.current_balance} BC available` : "insufficient balance"}`
              : "Each message burns AI Credits · Mock provider when no API key configured"}{" "}
            · AI is witness, not ruler
          </p>
          <NetworkNodesPanel
            fetchJson={fetchJson}
            onSelectEntity={openEntity}
            onRefreshGraph={() => goToTab("graph")}
          />
          {!profile ? (
            <p className="empty-state">Dev Login first to access the AI node.</p>
          ) : (
            <>
              <textarea
                className="field-textarea"
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                rows={4}
                placeholder="Query the contribution network…"
              />
              <div style={{ marginTop: 12 }}>
                <button
                  type="button"
                  className="btn btn--ai"
                  onClick={sendChat}
                  disabled={chatLoading || !chatMessage.trim() || chatQuote?.allowed === false}
                >
                  {chatLoading
                    ? "Transmitting…"
                    : `Send · ${chatQuote?.cost ?? "?"} Credits`}
                </button>
                {chatQuote?.allowed === false && (
                  <p className="wallet-audit-hint wallet-audit-hint--bad" style={{ marginTop: 8 }}>
                    Insufficient AI Credits — contribute or check Wallet tab
                  </p>
                )}
              </div>
              {chatReply && (
                <div className="chat-reply">
                  <div className="chat-reply__meta">
                    {chatReply.provider}/{chatReply.model} · spent {chatReply.credits_spent} · remaining{" "}
                    {chatReply.remaining_credits}
                  </div>
                  <div className="chat-reply__body">{chatReply.reply}</div>
                </div>
              )}
              {aiUsage.length > 0 && (
                <div style={{ marginTop: 20 }}>
                  <h3 style={{ fontSize: "0.85rem", marginBottom: 8, color: "var(--ai)" }}>Usage History</h3>
                  {aiUsage.slice(0, 10).map((u) => (
                    <div key={u.id} className="mini-card mini-card--credits">
                      <span style={{ color: "var(--text-dim)", fontFamily: "var(--mono)", fontSize: "0.72rem" }}>
                        {u.provider}/{u.model}
                      </span>
                      {" · "}
                      <span style={{ color: "var(--ai)" }}>-{u.credits_spent} Credits</span>
                      {(u.prompt || u.prompt_preview) && (
                        <div style={{ fontSize: "0.8rem", marginTop: 4, color: "var(--text-muted)" }}>
                          {(u.prompt || u.prompt_preview).slice(0, 80)}
                          {(u.prompt || u.prompt_preview).length > 80 ? "…" : ""}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </section>
      )}

      {tab === "studio" && (
        <AgentStudioPanel fetchJson={fetchJson} me={profile} />
      )}

      {tab === "ecosystem" && (
        <EcosystemPanel fetchJson={fetchJson} authenticated={!!profile} onSelectEntity={openEntity} />
      )}

      {tab === "provider" && (
        <>
          <CapabilityDirectory fetchJson={fetchJson} onSelectEntity={openEntity} />
          <ProviderPanel fetchJson={fetchJson} me={profile} entities={entities} />
          <ComputePoolPanel fetchJson={fetchJson} me={profile} entities={entities} />
        </>
      )}

      {tab === "workflow" && (
        <section className="panel">
          <AdvisoryBanner />
          <h2 className="panel__title">Contribution Pipeline</h2>
          <p className="panel__subtitle">
            Submit → AI advisory review → Human approval → CP + AI Credits → Ledger
          </p>
          <SubmitFlow
            api={API}
            entities={entities}
            tasks={tasks}
            currentEntityId={profile?.entity?.id || null}
            onComplete={load}
            onProofLink={(id) => {
              setProofContributionId(id);
              goToTab("verify");
            }}
            onSelectEntity={openEntity}
          />
        </section>
      )}

      {tab === "verify" && (
        <section className="panel">
          <h2 className="panel__title">Verify Contribution Proof</h2>
          <p className="panel__subtitle">
            Deep-link: <code>?proof=&lt;contribution_id&gt;</code> — audit hash chain and export portable proof JSON.
          </p>
          <label className="form-row">
            <span>Contribution ID</span>
            <input
              type="text"
              value={proofContributionId}
              onChange={(e) => setProofContributionId(e.target.value.trim())}
              placeholder="Paste contribution UUID from ledger or submit flow"
            />
          </label>
          {proofContributionId ? (
            <ProofVerifyPanel
              apiBase={API}
              contributionId={proofContributionId}
              fetchJson={fetchJson}
              onSelectEntity={openEntity}
              entityMap={entityMap}
            />
          ) : (
            <p className="panel__subtitle">Enter a contribution ID or open a shared proof link.</p>
          )}
        </section>
      )}

      {tab === "entities" && (
        <>
          {selectedEntity ? (
            <EntityDetail
              entity={selectedEntity}
              wallet={walletMap[selectedEntity.id]}
              reputationRows={reputationByEntity[selectedEntity.id] || []}
              contributions={contributions}
              entityMap={entityMap}
              onBack={() => setSelectedEntityId(null)}
              fetchJson={fetchJson}
              authenticated={!!profile}
              me={profile}
              onSelectEntity={openEntity}
              onOpenContribution={openContribution}
              onOpenLedger={openLedgerLink}
            />
          ) : (
            <section className="panel">
              <h2 className="panel__title">Entity Registry</h2>
              <p className="panel__subtitle">Click an entity for wallet, reputation, and contributions</p>
              {entities.map((e) => (
                <button
                  key={e.id}
                  type="button"
                  className="entity-row"
                  style={{ width: "100%", textAlign: "left", cursor: "pointer", border: "1px solid var(--border-subtle)" }}
                  onClick={() => setSelectedEntityId(e.id)}
                >
                  <EntityBadge type={e.entity_type} />
                  <span className="entity-row__name">{e.name}</span>
                  {GENESIS_IDS.has(e.id) && <span className="genesis-tag">GENESIS</span>}
                  {e.entity_type === "llm" && <span className="witness-tag">AI WITNESS</span>}
                  {e.metadata?.roles?.includes("external_inspiration") && (
                    <span className="inspiration-tag">INSPIRATION</span>
                  )}
                  {e.metadata?.roles?.includes("community_partner") && (
                    <span className="partner-tag">PARTNER</span>
                  )}
                  {(e.metadata?.roles?.includes("federation_peer") ||
                    e.metadata?.roles?.includes("federation_node")) && (
                    <span className="inspiration-tag">FEDERATION</span>
                  )}
                  {(e.metadata?.roles?.includes("federated_mirror") ||
                    e.metadata?.roles?.includes("remote_entity")) && (
                    <span className="remote-tag">REMOTE</span>
                  )}
                  <span className="entity-row__desc">{e.description}</span>
                </button>
              ))}
            </section>
          )}
        </>
      )}

      {tab === "graph" && (
        <section className="panel">
          <h2 className="panel__title section-heading--ai">Contribution Graph</h2>
          <p className="form-hint" style={{ marginBottom: 12 }}>
            Meta Agents (Nexus-0, Forge-0, …) sit in the dedicated <strong>meta_agent</strong> column
            (pink border, <strong>META AGENT</strong> label). Use <strong>Meta Agents only</strong> to focus
            the roster, and enable the <strong>Agent Studio</strong> layer for orchestration edges
            {graph?.meta_agent_nodes > 0
              ? ` (${graph.meta_agent_nodes} agents`
              : " — refresh after backend starts"}
            {graph?.edge_layer_counts?.studio > 0
              ? `, ${graph.edge_layer_counts.studio} studio edges).`
              : graph?.meta_agent_nodes > 0
                ? ")."
                : "."}
          </p>
          <ContributionGraphView graph={graph} entities={entities} />
        </section>
      )}

      {tab === "dashboard" && (
        <>
          <section className="panel panel--studio-cta">
            <div className="studio-cta">
              <div>
                <h2 className="panel__title" style={{ marginBottom: 4 }}>
                  Agent Studio
                </h2>
                <p className="panel__subtitle" style={{ margin: 0 }}>
                  15 Meta Agents · Nexus-0 PM · missions · handoffs · Cursor automation
                </p>
              </div>
              <button type="button" className="btn btn--primary" onClick={() => goToTab("studio")}>
                Open Agent Studio
              </button>
            </div>
          </section>
          <div className="stats-grid">
            <div className="stat-block">
              <div className="stat-block__label">Entities</div>
              <div className="stat-block__value">{entities.length}</div>
            </div>
            <div className="stat-block">
              <div className="stat-block__label">Contributions</div>
              <div className="stat-block__value stat-block__value--btc">{contributions.length}</div>
            </div>
            <div className="stat-block stat-block--ai">
              <div className="stat-block__label">Graph Edges</div>
              <div className="stat-block__value stat-block__value--ai">
                {graph.edges?.length ?? 0}
              </div>
            </div>
            <div className="stat-block stat-block--ai">
              <div className="stat-block__label">Ledger Blocks</div>
              <div className="stat-block__value stat-block__value--ai">{ledger.length}</div>
            </div>
          </div>

          <CryptoReadinessPanel
            readiness={cryptoReadiness}
            anchor={ledgerAnchor}
            ledgerVerify={ledgerVerify}
            walletAudit={walletAudit}
          />

          <section className="panel">
            <h2 className="panel__title">Registered Entities</h2>
            <p className="panel__subtitle">Humans · Agents · Skills · LLMs · Organizations</p>
            <div className="entity-filters" style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
              <select
                value={entityTypeFilter}
                onChange={(ev) => setEntityTypeFilter(ev.target.value)}
                aria-label="Filter by entity type"
                style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border, #e2e8f0)" }}
              >
                <option value="">All types</option>
                {["human", "agent", "skill", "llm", "tool", "dataset", "workflow", "organization", "community"].map(
                  (t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  )
                )}
              </select>
              <select
                value={entityStatusFilter}
                onChange={(ev) => setEntityStatusFilter(ev.target.value)}
                aria-label="Filter by status"
                style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border, #e2e8f0)" }}
              >
                <option value="">All statuses</option>
                <option value="active">active</option>
                <option value="pending">pending</option>
                <option value="inactive">inactive</option>
              </select>
              <button
                type="button"
                className="btn btn--secondary"
                onClick={() => load()}
                style={{ padding: "6px 12px" }}
              >
                Apply filters
              </button>
            </div>
            {entities.map((e) => (
              <div
                key={e.id}
                className="entity-row"
                role="button"
                tabIndex={0}
                onClick={() => {
                  setSelectedEntityId(e.id);
                  goToTab("entities");
                }}
                onKeyDown={(ev) => {
                  if (ev.key === "Enter") {
                    setSelectedEntityId(e.id);
                    goToTab("entities");
                  }
                }}
                style={{ cursor: "pointer" }}
              >
                <EntityBadge type={e.entity_type} />
                <span className="entity-row__name">{e.name}</span>
                {GENESIS_IDS.has(e.id) && <span className="genesis-tag">GENESIS</span>}
                {e.entity_type === "llm" && <span className="witness-tag">AI WITNESS</span>}
                {(e.metadata?.roles?.includes("federated_mirror") ||
                  e.metadata?.roles?.includes("remote_entity")) && (
                  <span className="remote-tag">REMOTE</span>
                )}
                <span className="entity-row__desc">{e.description}</span>
                {e.metadata?.mission && <span className="entity-row__mission">{e.metadata.mission}</span>}
              </div>
            ))}
          </section>

          {invocations.length > 0 && (
            <section className="panel">
              <h2 className="panel__title section-heading--ai">Invocation Chains</h2>
              {invocations.slice(0, 3).map((inv) => (
                <div key={inv.id} className="chain-row">
                  <strong>{entityMap[inv.initiator_id]?.name}</strong>
                  {inv.steps.map((s, i) => (
                    <span key={s.id}>
                      {i === 0 ? " " : <span className="chain-arrow"> → </span>}
                      <span className="chain-action">{s.action}</span>
                      <span className="chain-arrow"> → </span>
                      <strong>{entityMap[s.target_entity_id]?.name || (s.action === "invokes_llm" ? inv.model_provider : "?")}</strong>
                    </span>
                  ))}
                  {inv.model_provider && <span className="chain-arrow"> → {inv.model_provider}</span>}
                </div>
              ))}
            </section>
          )}

          {reviewQueue.length > 0 && (
            <section className="panel">
              <h2 className="panel__title">Finalization Queue</h2>
              <p className="panel__subtitle">Contributions awaiting policy finalization (optional manual queue)</p>
              {reviewQueue.map((item) => (
                <div key={item.contribution_id} className="mini-card">
                  <strong>{item.task_title || "Contribution"}</strong> — {item.description?.slice(0, 60)}
                  {item.description?.length > 60 ? "…" : ""}
                  <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: 4 }}>
                    By {item.primary_entity?.name || item.primary_entity?.id} · consensus pass:{" "}
                    {String(item.consensus_passed ?? "—")}
                  </div>
                </div>
              ))}
            </section>
          )}

          {contribution && (
            <section className="panel">
              <h2 className="panel__title">Latest Contribution Block</h2>
              <p className="panel__subtitle">{contribution.description}</p>
              <p>
                Status: <strong style={{ color: "var(--btc)" }}>{contribution.status}</strong>
              </p>
              {contribution.ai_verifications?.length > 0 && (
                <div style={{ margin: "1rem 0" }}>
                  <h3 style={{ fontSize: "0.85rem", margin: "0 0 0.5rem", color: "var(--ai)" }}>AI Witness Reviews</h3>
                  {contribution.ai_verifications.map((v) => (
                    <div key={v.id} className={`verify-card verify-card--${v.passed ? "pass" : "fail"}`}>
                      <span className="verify-card__provider">{v.model_provider}</span> — score {v.score} (
                      {v.passed ? "advisory pass" : "advisory fail"})
                      <div style={{ color: "var(--text-muted)", marginTop: 4 }}>{v.feedback}</div>
                    </div>
                  ))}
                </div>
              )}
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Entity</th>
                    <th>Type</th>
                    <th>Role</th>
                    <th>Weight</th>
                  </tr>
                </thead>
                <tbody>
                  {contribution.participants.map((p) => {
                    const entity = entityMap[p.entity_id];
                    return (
                      <tr key={p.id}>
                        <td>{entity?.name || p.entity_id}</td>
                        <td>
                          <EntityBadge type={entity?.entity_type} />
                        </td>
                        <td>{p.role}</td>
                        <td>{(p.weight * 100).toFixed(0)}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <ContributionInsights
                contributionId={contribution.id}
                fetchJson={fetchJson}
                onSelectEntity={openEntity}
              />
            </section>
          )}

          <div className="two-col">
            <section className="panel">
              <h2 className="panel__title">CP & AI Credits</h2>
              {wallets.map((w) => {
                const entity = entityMap[w.entity_id];
                return (
                  <div key={w.id} className="mini-card mini-card--credits">
                    <strong>{entity?.name}</strong>:{" "}
                    <span style={{ color: "var(--btc)" }}>{w.cp_balance} CP</span>,{" "}
                    <span style={{ color: "var(--ai)" }}>{w.ai_credits} Credits</span>
                  </div>
                );
              })}
            </section>
            <section className="panel">
              <h2 className="panel__title">Reputation</h2>
              {reputation.map((r) => {
                const entity = entityMap[r.entity_id];
                return (
                  <div key={r.id} className="mini-card mini-card--rep">
                    <strong>{entity?.name}</strong> ({r.category}): +{r.score}
                  </div>
                );
              })}
            </section>
          </div>

          {(focusedLedger || latestLedger) && (
            <div>
              {focusedLedger && (
                <div style={{ marginBottom: 8, display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="proof-layers__meta">Ledger record from wallet activity</span>
                  <button type="button" className="btn btn--ghost btn--sm" onClick={() => setFocusedLedgerHash(null)}>
                    Show latest
                  </button>
                </div>
              )}
              <LedgerBlockPanel
                record={focusedLedger || latestLedger}
                height={ledger.length}
              />
            </div>
          )}

          {contribution?.status === "approved" && (
            <ProofVerifyPanel
              apiBase={API}
              contributionId={contribution.id}
              fetchJson={fetchJson}
              onSelectEntity={openEntity}
              entityMap={entityMap}
            />
          )}
        </>
      )}
    </div>
  );
}
