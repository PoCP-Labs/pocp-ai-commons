import { useCallback, useEffect, useState } from "react";

const KIND_FILTERS = [
  { value: "", label: "All" },
  { value: "compute", label: "Compute" },
  { value: "capability", label: "Capabilities" },
];

export default function CapabilityDirectory({ fetchJson, onSelectEntity }) {
  const [items, setItems] = useState([]);
  const [exchangeKind, setExchangeKind] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadDirectory = useCallback(async () => {
    if (!fetchJson) return;
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: "50" });
      if (exchangeKind) params.set("exchange_kind", exchangeKind);
      const data = await fetchJson(`/api/v1/capabilities/directory?${params}`);
      setItems(data.items || []);
    } catch (err) {
      setError(err.message);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [exchangeKind, fetchJson]);

  useEffect(() => {
    loadDirectory();
  }, [loadDirectory]);

  return (
    <section className="panel">
      <h2 className="panel__title section-heading--ai">Compute &amp; Capabilities</h2>
      <p className="panel__subtitle">
        Browse provider Entities — metered compute and AI capabilities on the network
      </p>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        {KIND_FILTERS.map((opt) => (
          <button
            key={opt.value || "all"}
            type="button"
            className={`btn btn--sm ${exchangeKind === opt.value ? "btn--primary" : "btn--secondary"}`}
            onClick={() => setExchangeKind(opt.value)}
          >
            {opt.label}
          </button>
        ))}
        <button type="button" className="btn btn--sm btn--ghost" onClick={loadDirectory} disabled={loading}>
          Refresh
        </button>
      </div>

      {loading && <p className="empty-state">Loading directory…</p>}
      {error && <p className="alert alert--info">{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p className="empty-state">No providers published yet. Use Provider Panel to register.</p>
      )}

      {items.map((item) => (
        <div key={`${item.provider_entity_id}-${item.capability_id || item.capability_type}`} className="mini-card">
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
            <strong>{item.name}</strong>
            <span className={`entity-badge entity-badge--${item.exchange_kind === "compute" ? "llm" : "skill"}`}>
              {item.exchange_kind}
            </span>
          </div>
          <div className="entity-row__mission" style={{ marginTop: 6 }}>
            Provider:{" "}
            {onSelectEntity ? (
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                style={{ padding: 0, minHeight: 0 }}
                onClick={() => onSelectEntity(item.provider_entity_id)}
              >
                {item.provider_name}
              </button>
            ) : (
              item.provider_name
            )}{" "}
            · {item.capability_type} · {item.unit}
            {item.base_price != null ? ` · ${item.base_price} AIC` : ""}
          </div>
          <div className="entity-row__mission" style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
            {item.source} · {item.availability || "—"}
          </div>
        </div>
      ))}
    </section>
  );
}
