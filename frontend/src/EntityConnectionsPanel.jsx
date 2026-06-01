import { useEffect, useState } from "react";

const LAYER_TABS = [
  { id: "structural", label: "Structural", labelZh: "结构层" },
  { id: "protocol", label: "Protocol", labelZh: "贡献协议" },
  { id: "operational", label: "Operational", labelZh: "运行迹" },
];

function EntityLink({ brief, onSelectEntity }) {
  if (!brief) return <span className="conn-muted">—</span>;
  return (
    <button type="button" className="conn-entity-link" onClick={() => onSelectEntity?.(brief.entity_id)}>
      <span className={`entity-badge entity-badge--${brief.entity_type || "llm"}`}>{brief.entity_type}</span>
      <span>{brief.name || brief.entity_id?.slice(0, 8)}</span>
    </button>
  );
}

function StepRow({ step, onSelectEntity }) {
  return (
    <div className="conn-step">
      <span className="conn-step__order">{step.step_order}</span>
      <EntityLink brief={step.source} onSelectEntity={onSelectEntity} />
      <span className="chain-action">{step.action}</span>
      <EntityLink brief={step.target} onSelectEntity={onSelectEntity} />
      {step.has_capability_receipt && <span className="conn-receipt-tag">receipt</span>}
    </div>
  );
}

export default function EntityConnectionsPanel({ entityId, fetchJson, onSelectEntity, ontologyConnections }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [layer, setLayer] = useState("structural");

  useEffect(() => {
    if (!fetchJson || !entityId) return;
    let cancelled = false;
    setLoading(true);
    fetchJson(`/api/v1/entities/${entityId}/connections`)
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch(() => {
        if (!cancelled) setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [entityId, fetchJson]);

  const allowed = data?.allowed || ontologyConnections || {};
  const structural = data?.structural || {};
  const protocol = data?.protocol || {};
  const operational = data?.operational || {};

  return (
    <div className="conn-panel">
      <div className="conn-panel__header">
        <div>
          <strong>Protocol connections</strong>
          <div className="conn-panel__hint">万物互联于贡献协议 · structural · protocol · operational</div>
        </div>
        {data?.matrix_api && (
          <span className="conn-muted" title="Type-level matrix API">
            {allowed.schema || "pocp.entity_connection.v0.1"}
          </span>
        )}
      </div>

      {(allowed.can_own_types?.length > 0 || allowed.typical_invocation_targets?.length > 0) && (
        <div className="conn-allowed">
          {allowed.can_own_types?.length > 0 && (
            <div>
              <span className="conn-label">Can own</span>
              {allowed.can_own_types.map((t) => (
                <span key={t} className={`entity-badge entity-badge--${t}`}>
                  {t}
                </span>
              ))}
            </div>
          )}
          {Object.keys(allowed.suggested_invocation_actions || {}).length > 0 && (
            <div style={{ marginTop: 8 }}>
              <span className="conn-label">Invoke</span>
              {Object.entries(allowed.suggested_invocation_actions).map(([target, action]) => (
                <span key={target} className="conn-invoke-chip">
                  → {target} <em>({action})</em>
                </span>
              ))}
            </div>
          )}
          {(allowed.typical_participant_roles || []).length > 0 && (
            <div style={{ marginTop: 8, fontSize: "0.75rem", color: "var(--text-dim)" }}>
              Roles: {allowed.typical_participant_roles.join(", ")}
            </div>
          )}
        </div>
      )}

      <div className="conn-tabs">
        {LAYER_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`conn-tab${layer === tab.id ? " conn-tab--active" : ""}`}
            onClick={() => setLayer(tab.id)}
          >
            {tab.label}
            <span className="conn-tab__zh">{tab.labelZh}</span>
          </button>
        ))}
      </div>

      {loading && <p className="proof-layers__meta">Loading connections…</p>}

      {!loading && layer === "structural" && (
        <div className="conn-layer">
          <div className="conn-stat-row">
            <span>Owner</span>
            <EntityLink brief={structural.owner} onSelectEntity={onSelectEntity} />
          </div>
          <div className="conn-stat-row">
            <span>Owned ({structural.owned_count ?? 0})</span>
            <div className="conn-list">
              {(structural.owned || []).length === 0 ? (
                <span className="conn-muted">None</span>
              ) : (
                structural.owned.map((e) => (
                  <EntityLink key={e.entity_id} brief={e} onSelectEntity={onSelectEntity} />
                ))
              )}
            </div>
          </div>
          <div className="conn-stat-row">
            <span>Created ({structural.created_count ?? 0})</span>
            <div className="conn-list">
              {(structural.created || []).length === 0 ? (
                <span className="conn-muted">None</span>
              ) : (
                structural.created.map((e) => (
                  <EntityLink key={e.entity_id} brief={e} onSelectEntity={onSelectEntity} />
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {!loading && layer === "protocol" && (
        <div className="conn-layer">
          <div className="conn-stat-row">
            <span>Participations</span>
            <strong>{protocol.participation_count ?? 0}</strong>
          </div>
          {(protocol.roles_seen || []).length > 0 && (
            <div className="conn-stat-row">
              <span>Roles seen</span>
              <div className="conn-list">
                {protocol.roles_seen.map((r) => (
                  <span key={r} className="conn-role-chip">
                    {r}
                  </span>
                ))}
              </div>
            </div>
          )}
          {(protocol.participations || []).slice(0, 8).map((p) => (
            <div key={`${p.contribution_id}-${p.role}`} className="mini-card conn-participation">
              <span className="conn-role-chip">{p.role}</span>
              <span className="conn-muted"> · weight {p.weight}</span>
              <div className="conn-muted" style={{ marginTop: 4 }}>
                {p.contribution_status} · {p.contribution_id?.slice(0, 12)}…
              </div>
            </div>
          ))}
          {(protocol.participations || []).length === 0 && (
            <p className="conn-muted">No contribution participant links yet.</p>
          )}
        </div>
      )}

      {!loading && layer === "operational" && (
        <div className="conn-layer">
          <div className="conn-stats-grid">
            <div className="conn-mini-stat">
              <span>Traces initiated</span>
              <strong>{operational.traces_initiated_count ?? 0}</strong>
            </div>
            <div className="conn-mini-stat">
              <span>Outbound steps</span>
              <strong>{operational.outbound_step_count ?? 0}</strong>
            </div>
            <div className="conn-mini-stat">
              <span>Inbound steps</span>
              <strong>{operational.inbound_step_count ?? 0}</strong>
            </div>
          </div>
          {(operational.outbound_steps || []).length > 0 && (
            <>
              <div className="conn-label" style={{ marginTop: 12 }}>
                Outbound
              </div>
              {operational.outbound_steps.map((s) => (
                <StepRow key={s.step_id} step={s} onSelectEntity={onSelectEntity} />
              ))}
            </>
          )}
          {(operational.inbound_steps || []).length > 0 && (
            <>
              <div className="conn-label" style={{ marginTop: 12 }}>
                Inbound
              </div>
              {operational.inbound_steps.map((s) => (
                <StepRow key={s.step_id} step={s} onSelectEntity={onSelectEntity} />
              ))}
            </>
          )}
          {(operational.outbound_steps || []).length === 0 &&
            (operational.inbound_steps || []).length === 0 && (
              <p className="conn-muted">No invocation trace steps recorded.</p>
            )}
        </div>
      )}
    </div>
  );
}
