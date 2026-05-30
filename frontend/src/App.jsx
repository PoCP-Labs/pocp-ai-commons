import { useCallback, useEffect, useState } from "react";
import ContributionGraphView from "./ContributionGraph";
import SkillDetail from "./SkillDetail";
import SubmitFlow from "./SubmitFlow";
import UserMenu from "./auth/UserMenu";
import { useAuth, publicGet } from "./auth";

const ENTITY_COLORS = {
  human: "#2563eb",
  agent: "#7c3aed",
  skill: "#059669",
  organization: "#d97706",
  llm: "#64748b",
};

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
  const { user } = useAuth();
  const [entities, setEntities] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [contributions, setContributions] = useState([]);
  const [invocations, setInvocations] = useState([]);
  const [wallets, setWallets] = useState([]);
  const [reputation, setReputation] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("dashboard");
  const [selectedSkillId, setSelectedSkillId] = useState(null);

  const load = useCallback(() => {
    setError(null);
    return Promise.all([
      publicGet("/api/v1/entities"),
      publicGet("/api/v1/tasks"),
      publicGet("/api/v1/contributions"),
      publicGet("/api/v1/invocations"),
      publicGet("/api/v1/wallets"),
      publicGet("/api/v1/reputation"),
      publicGet("/api/v1/ledger"),
      publicGet("/api/v1/graph"),
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
    load();
  }, [load]);

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
      <header style={{ marginBottom: "1.5rem", display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ margin: 0 }}>PoCP AI Commons</h1>
          <p style={{ color: "#475569", marginTop: 8 }}>
            Entity-Centric Proof of Contribution Protocol — V0.2
          </p>
        </div>
        <UserMenu />
      </header>

      <nav style={{ display: "flex", gap: 4, marginBottom: "1.5rem", borderBottom: "1px solid #e2e8f0" }}>
        <button type="button" style={tabStyle("dashboard")} onClick={() => setTab("dashboard")}>Dashboard</button>
        <button type="button" style={tabStyle("workflow")} onClick={() => setTab("workflow")}>Submit Workflow</button>
        <button type="button" style={tabStyle("graph")} onClick={() => setTab("graph")}>Contribution Graph</button>
      </nav>

      {error && (
        <p style={{ color: "#dc2626", marginBottom: 16 }}>
          API unavailable ({error}). Start backend: <code>docker compose up backend</code>
        </p>
      )}

      {tab === "workflow" && (
        <section style={{ marginBottom: "2rem" }}>
          <h2>Multi-Entity Contribution Workflow</h2>
          <p style={{ color: "#64748b", marginBottom: 16 }}>
            Invoke → Submit → AI Verify → Human Approve → Credits + Reputation
          </p>
          <SubmitFlow entities={entities} tasks={tasks} onComplete={load} user={user} />
        </section>
      )}

      {tab === "graph" && (
        <section>
          <h2>Intelligence Contribution Graph</h2>
          <p style={{ color: "#64748b" }}>
            {graph.nodes.length} entity nodes · {graph.edges.length} edges · {contributions.length} contributions · {ledger.length} ledger entries
          </p>
          <ContributionGraphView
            graph={graph}
            entityMap={entityMap}
            contributions={contributions}
            ledger={ledger}
          />
        </section>
      )}

      {tab === "dashboard" && (
        <>
          <section style={{ marginBottom: "2rem" }}>
            <h2>Entities</h2>
            <div style={{ display: "grid", gap: 12 }}>
              {entities.map((e) => {
                const isClickable = e.entity_type === "skill";
                return (
                  <div
                    key={e.id}
                    onClick={() => isClickable && setSelectedSkillId(e.id)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      padding: 12,
                      background: "#f8fafc",
                      borderRadius: 8,
                      cursor: isClickable ? "pointer" : "default",
                      transition: "background 0.15s",
                    }}
                    onMouseEnter={(ev) => {
                      if (isClickable) ev.currentTarget.style.background = "#e2e8f0";
                    }}
                    onMouseLeave={(ev) => {
                      if (isClickable) ev.currentTarget.style.background = "#f8fafc";
                    }}
                    role={isClickable ? "button" : undefined}
                    tabIndex={isClickable ? 0 : undefined}
                    onKeyDown={(ev) => {
                      if (isClickable && (ev.key === "Enter" || ev.key === " ")) {
                        ev.preventDefault();
                        setSelectedSkillId(e.id);
                      }
                    }}
                  >
                    <EntityBadge type={e.entity_type} />
                    <strong>{e.name}</strong>
                    <span style={{ color: "#64748b", fontSize: 14 }}>{e.description}</span>
                    {e.entity_type === "skill" && (
                      <span style={{ marginLeft: "auto", fontSize: 12, color: "#059669" }}>
                        View details →
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          {selectedSkillId && (
            <div
              style={{
                position: "fixed",
                inset: 0,
                background: "rgba(0,0,0,0.3)",
                display: "flex",
                justifyContent: "center",
                alignItems: "flex-start",
                paddingTop: "3rem",
                zIndex: 100,
                overflow: "auto",
              }}
              onClick={(ev) => {
                if (ev.target === ev.currentTarget) setSelectedSkillId(null);
              }}
            >
              <div
                style={{
                  background: "#fff",
                  borderRadius: 12,
                  padding: "2rem",
                  width: "90%",
                  maxWidth: 700,
                  maxHeight: "85vh",
                  overflow: "auto",
                  boxShadow: "0 20px 60px rgba(0,0,0,0.15)",
                }}
              >
                <SkillDetail
                  skillId={selectedSkillId}
                  onBack={() => setSelectedSkillId(null)}
                />
              </div>
            </div>
          )}

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
