import { useCallback, useEffect, useState } from "react";
import ContributionGraphView from "./ContributionGraph";
import SubmitFlow from "./SubmitFlow";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const TOKEN_KEY = "pocp_token";

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function fetchJson(path, options = {}) {
  const token = getToken();
  const headers = {
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

const ENTITY_COLORS = {
  human: "#2563eb",
  agent: "#7c3aed",
  skill: "#059669",
  organization: "#d97706",
  llm: "#64748b",
};

const GENESIS_IDS = new Set(["pocp-entity-lumen-0", "pocp-entity-desui"]);

function EntityBadge({ type }) {
  return (
    <span
      style={{
        background: ENTITY_COLORS[type] || "#64748b",
        color: "#fff",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 12,
        fontWeight: 600,
        textTransform: "uppercase",
      }}
    >
      {type}
    </span>
  );
}

export default function App() {
  const [entities, setEntities] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [contributions, setContributions] = useState([]);
  const [invocations, setInvocations] = useState([]);
  const [wallets, setWallets] = useState([]);
  const [reputation, setReputation] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [profile, setProfile] = useState(null);
  const [chatMessage, setChatMessage] = useState("");
  const [chatReply, setChatReply] = useState(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("dashboard");

  const loadProfile = useCallback(async () => {
    if (!getToken()) {
      setProfile(null);
      return;
    }
    try {
      const me = await fetchJson("/api/v1/me");
      setProfile(me);
    } catch {
      setToken(null);
      setProfile(null);
    }
  }, []);

  const load = useCallback(() => {
    setError(null);
    return Promise.all([
      fetchJson("/api/v1/entities"),
      fetchJson("/api/v1/tasks"),
      fetchJson("/api/v1/contributions"),
      fetchJson("/api/v1/invocations"),
      fetchJson("/api/v1/wallets"),
      fetchJson("/api/v1/reputation"),
      fetchJson("/api/v1/ledger"),
      fetchJson("/api/v1/graph"),
    ])
      .then(([e, t, c, inv, w, r, l, g]) => {
        setEntities(e);
        setTasks(t);
        setContributions(c);
        setInvocations(inv);
        setWallets(w);
        setReputation(r);
        setLedger(l);
        setGraph(g);
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get("token");
    if (urlToken) {
      setToken(urlToken);
      params.delete("token");
      const next = `${window.location.pathname}${params.toString() ? `?${params}` : ""}`;
      window.history.replaceState({}, "", next);
    }
    load();
    loadProfile();
  }, [load, loadProfile]);

  const devLogin = async () => {
    setAuthLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/v1/auth/dev-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: `dev-${Date.now().toString(36)}`,
          email: `dev-${Date.now()}@example.com`,
        }),
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
      await loadProfile();
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setChatLoading(false);
    }
  };

  const entityMap = Object.fromEntries(entities.map((e) => [e.id, e]));
  const contribution = contributions[0];

  const tabStyle = (name) => ({
    padding: "8px 16px",
    border: "none",
    borderBottom: tab === name ? "2px solid #2563eb" : "2px solid transparent",
    background: "none",
    cursor: "pointer",
    fontWeight: tab === name ? 600 : 400,
    color: tab === name ? "#2563eb" : "#64748b",
  });

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", maxWidth: 1000, margin: "0 auto", padding: "2rem" }}>
      <header style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, flexWrap: "wrap" }}>
          <div>
            <h1 style={{ margin: 0 }}>PoCP AI Commons</h1>
            <p style={{ color: "#475569", marginTop: 8 }}>
              Entity-Centric Proof of Contribution Protocol — Sprint Alpha
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            {profile ? (
              <>
                <span style={{ fontSize: 14, color: "#334155" }}>
                  {profile.user.username} · {profile.wallet.ai_credits} AI Credits
                </span>
                <button type="button" onClick={logout} style={{ padding: "6px 12px", cursor: "pointer" }}>
                  Logout
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={devLogin}
                disabled={authLoading}
                style={{ padding: "8px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}
              >
                {authLoading ? "Logging in…" : "Dev Login"}
              </button>
            )}
          </div>
        </div>
      </header>

      <nav style={{ display: "flex", gap: 4, marginBottom: "1.5rem", borderBottom: "1px solid #e2e8f0", flexWrap: "wrap" }}>
        <button type="button" style={tabStyle("dashboard")} onClick={() => setTab("dashboard")}>Dashboard</button>
        <button type="button" style={tabStyle("account")} onClick={() => setTab("account")}>Account</button>
        <button type="button" style={tabStyle("chat")} onClick={() => setTab("chat")}>AI Chat</button>
        <button type="button" style={tabStyle("workflow")} onClick={() => setTab("workflow")}>Submit Workflow</button>
        <button type="button" style={tabStyle("graph")} onClick={() => setTab("graph")}>Contribution Graph</button>
      </nav>

      {error && (
        <p style={{ color: "#dc2626", marginBottom: 16 }}>
          {error.includes("fetch") ? `API unavailable (${error}). Start backend: docker compose up backend` : error}
        </p>
      )}

      {tab === "account" && (
        <section>
          <h2>Profile & Wallet</h2>
          {!profile ? (
            <p style={{ color: "#64748b" }}>Dev Login to create a Human Entity, Wallet, and 100 starter AI Credits.</p>
          ) : (
            <div style={{ display: "grid", gap: 12 }}>
              <div style={{ padding: 16, background: "#f8fafc", borderRadius: 8 }}>
                <strong>{profile.entity.name}</strong>
                <div style={{ color: "#64748b", fontSize: 14, marginTop: 4 }}>{profile.user.email}</div>
                <div style={{ marginTop: 8 }}><EntityBadge type={profile.entity.entity_type} /></div>
              </div>
              <div style={{ padding: 16, background: "#f0fdf4", borderRadius: 8 }}>
                <div><strong>{profile.wallet.cp_balance}</strong> CP</div>
                <div><strong>{profile.wallet.ai_credits}</strong> AI Credits remaining</div>
              </div>
            </div>
          )}
        </section>
      )}

      {tab === "chat" && (
        <section>
          <h2>AI Chat</h2>
          <p style={{ color: "#64748b", marginBottom: 16 }}>
            Each message burns 5 AI Credits (mock provider when no API key is configured).
          </p>
          {!profile ? (
            <p style={{ color: "#64748b" }}>Dev Login first to use AI Chat.</p>
          ) : (
            <>
              <textarea
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                rows={4}
                placeholder="Ask PoCP AI Commons…"
                style={{ width: "100%", padding: 12, borderRadius: 8, border: "1px solid #e2e8f0", marginBottom: 8 }}
              />
              <button
                type="button"
                onClick={sendChat}
                disabled={chatLoading || !chatMessage.trim()}
                style={{ padding: "8px 16px", background: "#059669", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}
              >
                {chatLoading ? "Sending…" : "Send (5 credits)"}
              </button>
              {chatReply && (
                <div style={{ marginTop: 16, padding: 16, background: "#f1f5f9", borderRadius: 8 }}>
                  <div style={{ fontSize: 13, color: "#64748b", marginBottom: 8 }}>
                    {chatReply.provider}/{chatReply.model} · spent {chatReply.credits_spent} · remaining {chatReply.remaining_credits}
                  </div>
                  <div>{chatReply.reply}</div>
                </div>
              )}
            </>
          )}
        </section>
      )}

      {tab === "workflow" && (
        <section style={{ marginBottom: "2rem" }}>
          <h2>Multi-Entity Contribution Workflow</h2>
          <p style={{ color: "#64748b", marginBottom: 16 }}>
            Invoke → Submit → AI Verify → Human Approve → Credits + Reputation
          </p>
          <SubmitFlow api={API} entities={entities} tasks={tasks} currentEntityId={profile?.entity?.id || null} onComplete={load} />
        </section>
      )}

      {tab === "graph" && (
        <section>
          <h2>Intelligence Contribution Graph</h2>
          <p style={{ color: "#64748b" }}>
            {graph.nodes.length} nodes · {graph.edges.length} edges (includes invocation chains)
          </p>
          <ContributionGraphView graph={graph} entityMap={entityMap} />
        </section>
      )}

      {tab === "dashboard" && (
        <>
          <section style={{ marginBottom: "2rem" }}>
            <h2>Entities</h2>
            <div style={{ display: "grid", gap: 12 }}>
              {entities.map((e) => (
                <div key={e.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: 12, background: "#f8fafc", borderRadius: 8, flexWrap: "wrap" }}>
                  <EntityBadge type={e.entity_type} />
                  <strong>{e.name}</strong>
                  {GENESIS_IDS.has(e.id) && (
                    <span style={{ fontSize: 11, fontWeight: 600, color: "#7c3aed", background: "#ede9fe", padding: "2px 8px", borderRadius: 4 }}>
                      GENESIS
                    </span>
                  )}
                  <span style={{ color: "#64748b", fontSize: 14 }}>{e.description}</span>
                  {e.metadata?.mission && (
                    <span style={{ color: "#94a3b8", fontSize: 12, width: "100%" }}>{e.metadata.mission}</span>
                  )}
                </div>
              ))}
            </div>
          </section>

          {invocations.length > 0 && (
            <section style={{ marginBottom: "2rem" }}>
              <h2>Invocation Chains</h2>
              {invocations.slice(0, 3).map((inv) => (
                <div key={inv.id} style={{ padding: 12, background: "#f8fafc", borderRadius: 8, marginBottom: 8, fontSize: 14 }}>
                  <strong>{entityMap[inv.initiator_id]?.name}</strong>
                  {inv.steps.map((s, i) => (
                    <span key={s.id} style={{ color: "#64748b" }}>
                      {i === 0 ? " " : " → "}
                      <span style={{ color: "#334155" }}>{s.action}</span>
                      {" → "}
                      <strong>{entityMap[s.target_entity_id]?.name || (s.action === "invokes_llm" ? inv.model_provider : "?")}</strong>
                    </span>
                  ))}
                  {inv.model_provider && (
                    <span style={{ color: "#94a3b8" }}> → {inv.model_provider}</span>
                  )}
                </div>
              ))}
            </section>
          )}

          {contribution && (
            <section style={{ marginBottom: "2rem" }}>
              <h2>Latest Contribution</h2>
              <p style={{ color: "#64748b" }}>{contribution.description}</p>
              <p>Status: <strong>{contribution.status}</strong></p>
              {contribution.ai_verifications?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <h3 style={{ fontSize: 14, margin: "0 0 8px" }}>AI verifications</h3>
                  {contribution.ai_verifications.map((v) => (
                    <div key={v.id} style={{ padding: 10, background: "#f1f5f9", borderRadius: 6, marginBottom: 6, fontSize: 13 }}>
                      <strong>{v.model_provider}</strong> — score {v.score} ({v.passed ? "pass" : "fail"})
                      <div style={{ color: "#64748b", marginTop: 4 }}>{v.feedback}</div>
                    </div>
                  ))}
                </div>
              )}
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ textAlign: "left", borderBottom: "2px solid #e2e8f0" }}>
                    <th style={{ padding: 8 }}>Entity</th>
                    <th style={{ padding: 8 }}>Type</th>
                    <th style={{ padding: 8 }}>Role</th>
                    <th style={{ padding: 8 }}>Weight</th>
                  </tr>
                </thead>
                <tbody>
                  {contribution.participants.map((p) => {
                    const entity = entityMap[p.entity_id];
                    return (
                      <tr key={p.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                        <td style={{ padding: 8 }}>{entity?.name || p.entity_id}</td>
                        <td style={{ padding: 8 }}><EntityBadge type={entity?.entity_type} /></td>
                        <td style={{ padding: 8 }}>{p.role}</td>
                        <td style={{ padding: 8 }}>{(p.weight * 100).toFixed(0)}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </section>
          )}

          <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
            <div>
              <h2>AI Credits & CP</h2>
              {wallets.map((w) => {
                const entity = entityMap[w.entity_id];
                return (
                  <div key={w.id} style={{ padding: 12, background: "#f0fdf4", borderRadius: 8, marginBottom: 8 }}>
                    <strong>{entity?.name}</strong>: {w.cp_balance} CP, {w.ai_credits} AI Credits
                  </div>
                );
              })}
            </div>
            <div>
              <h2>Reputation</h2>
              {reputation.map((r) => {
                const entity = entityMap[r.entity_id];
                return (
                  <div key={r.id} style={{ padding: 12, background: "#faf5ff", borderRadius: 8, marginBottom: 8 }}>
                    <strong>{entity?.name}</strong> ({r.category}): +{r.score}
                  </div>
                );
              })}
            </div>
          </section>

          {ledger.length > 0 && (
            <section style={{ marginTop: "2rem" }}>
              <h2>Ledger</h2>
              <pre style={{ background: "#1e293b", color: "#e2e8f0", padding: 16, borderRadius: 8, overflow: "auto", fontSize: 13 }}>
                {JSON.stringify(ledger[0].payload, null, 2)}
              </pre>
            </section>
          )}
        </>
      )}
    </main>
  );
}
