import { useMemo } from "react";

function EntityBadge({ type }) {
  const safe = type || "llm";
  return <span className={`entity-badge entity-badge--${safe}`}>{safe}</span>;
}

export default function EntityDetail({ entity, wallet, reputationRows, contributions, entityMap, onBack }) {
  const relatedContributions = useMemo(
    () =>
      contributions.filter(
        (c) =>
          c.primary_entity_id === entity.id ||
          c.participants?.some((p) => p.entity_id === entity.id)
      ),
    [contributions, entity.id]
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
            <EntityBadge type={entity.entity_type} />
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
          {entity.metadata?.genesis_manifesto_primary && (
            <div className="entity-row__mission" style={{ marginTop: 8 }}>
              Genesis manifesto: {entity.metadata.genesis_manifesto_primary}
            </div>
          )}
          {entity.metadata?.genesis_manifesto_paths?.length > 0 && !entity.metadata?.genesis_manifesto_primary && (
            <div className="entity-row__mission" style={{ marginTop: 8 }}>
              Genesis manifesto: {entity.metadata.genesis_manifesto_paths[0]}
            </div>
          )}
          {entity.metadata?.org_founded && (
            <div className="entity-row__mission" style={{ marginTop: 8 }}>
              Founded org: {entity.metadata.org_founded}
            </div>
          )}
          {entity.metadata?.founded_by_name && (
            <div className="entity-row__mission" style={{ marginTop: 8 }}>
              Founded by: {entity.metadata.founded_by_name}
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

      {entity.entity_type === "skill" && (
        <div className="alert alert--info" style={{ marginTop: 12 }}>
          Skill entities power invocation chains. Full Skill Commons registry is a Phase 5 roadmap item.
        </div>
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
