import { useEffect, useState } from "react";

export default function EntityDetail({
  entity,
  wallet,
  reputationRows,
  contributions,
  entityMap,
  onBack,
  fetchJson,
}) {
  const [audit, setAudit] = useState([]);
  const [portable, setPortable] = useState(null);
  const [agentRep, setAgentRep] = useState(null);

  useEffect(() => {
    if (!fetchJson || !entity?.id) return;
    let cancelled = false;

    fetchJson(`/api/v1/entities/${entity.id}/reputation/audit?limit=8`)
      .then((data) => {
        if (!cancelled) setAudit(data.entries || []);
      })
      .catch(() => {
        if (!cancelled) setAudit([]);
      });

    fetchJson(`/api/v1/entities/${entity.id}/reputation/portable`)
      .then((data) => {
        if (!cancelled) setPortable(data);
      })
      .catch(() => {
        if (!cancelled) setPortable(null);
      });

    if (entity.entity_type === "agent") {
      fetchJson(`/api/v1/agents/${entity.id}/reputation/summary`)
        .then((data) => {
          if (!cancelled) setAgentRep(data);
        })
        .catch(() => {
          if (!cancelled) setAgentRep(null);
        });
    }

    return () => {
      cancelled = true;
    };
  }, [entity?.id, entity?.entity_type, fetchJson]);

  const relatedContributions = contributions.filter(
    (c) =>
      c.primary_entity_id === entity.id ||
      c.participants?.some((p) => p.entity_id === entity.id)
  );

  return (
    <section className="panel">
      <button type="button" className="btn btn--ghost" onClick={onBack} style={{ marginBottom: 12 }}>
        ← Back to Network
      </button>
      <h2 className="panel__title">{entity.name}</h2>
      <p className="panel__subtitle">{entity.description}</p>

      <div className="profile-grid" style={{ marginBottom: 16 }}>
        <div className="profile-card">
          <div style={{ marginBottom: 8 }}>
            <span className={`entity-badge entity-badge--${entity.entity_type || "llm"}`}>
              {entity.entity_type}
            </span>
          </div>
          <div className="entity-row__mission">ID: {entity.id}</div>
          {entity.metadata?.mission && (
            <div className="entity-row__mission" style={{ marginTop: 8 }}>
              {entity.metadata.mission}
            </div>
          )}
          {entity.metadata?.portable_id && (
            <div className="entity-row__mission">Portable: {entity.metadata.portable_id}</div>
          )}
          {entity.metadata?.roles?.length > 0 && (
            <div className="entity-row__mission" style={{ marginTop: 8 }}>
              Roles: {entity.metadata.roles.join(", ")}
            </div>
          )}
        </div>

        {wallet && (
          <div className="profile-card profile-card--wallet">
            <div className="profile-card__balance">
              <strong>{wallet.cp_balance}</strong> CP
            </div>
            <div className="profile-card__balance">
              <span className="ai-credits">
                <strong>{wallet.ai_credits}</strong>
              </span>{" "}
              AI Credits
            </div>
          </div>
        )}
      </div>

      {portable?.federation?.total_score > 0 && (
        <div className="mini-card mini-card--rep" style={{ marginBottom: 12 }}>
          Portable reputation total: <strong>{portable.federation.total_score}</strong>
          {portable.federation.federated_import_count > 0 && (
            <span> · {portable.federation.federated_import_count} federated import(s)</span>
          )}
        </div>
      )}

      {agentRep && agentRep.feedback_count > 0 && (
        <>
          <h3 style={{ fontSize: "0.9rem", marginBottom: 8 }}>Agent Feedback (ERC-8004 off-chain)</h3>
          <div className="mini-card mini-card--rep">
            Avg score: <strong>{agentRep.average_score}</strong> · Reviewers:{" "}
            <strong>{agentRep.unique_reviewers}</strong>
          </div>
        </>
      )}

      {reputationRows.length > 0 && (
        <>
          <h3 style={{ fontSize: "0.9rem", marginBottom: 8 }}>Reputation</h3>
          {reputationRows.map((r) => (
            <div key={r.id} className="mini-card mini-card--rep">
              {r.category}: +{r.score}
            </div>
          ))}
        </>
      )}

      {audit.length > 0 && (
        <>
          <h3 style={{ fontSize: "0.9rem", margin: "16px 0 8px" }}>Reputation Audit Trail</h3>
          {audit.map((entry) => (
            <div key={entry.id} className="mini-card">
              <strong>{entry.source}</strong> · {entry.category} · delta {entry.delta} → {entry.balance_after}
              {entry.reason && (
                <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: 4 }}>{entry.reason}</div>
              )}
            </div>
          ))}
        </>
      )}

      {relatedContributions.length > 0 && (
        <>
          <h3 style={{ fontSize: "0.9rem", margin: "16px 0 8px" }}>Related Contributions</h3>
          {relatedContributions.slice(0, 5).map((c) => (
            <div key={c.id} className="mini-card">
              <strong style={{ color: "var(--btc)" }}>{c.status}</strong> — {c.description?.slice(0, 80)}
              {c.description?.length > 80 ? "…" : ""}
              <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: 4 }}>
                Primary: {entityMap[c.primary_entity_id]?.name || c.primary_entity_id}
              </div>
            </div>
          ))}
        </>
      )}
    </section>
  );
}
