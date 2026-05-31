import { useCallback, useEffect, useState } from "react";

import LogOutreachForm from "./LogOutreachForm";

const PARTNER_STATUS = {
  prospect: "Prospect",
  outreach: "Outreach",
  in_conversation: "In conversation",
  active_partner: "Active partner",
  federation_peer: "Federation peer",
  integrated: "Integrated",
  paused: "Paused",
  declined: "Declined",
};

const CAPABILITY_OPTIONS = [
  { value: "llm_inference", label: "LLM inference" },
  { value: "training", label: "Training" },
  { value: "embeddings", label: "Embeddings" },
  { value: "witness", label: "Witness" },
  { value: "mcp_host", label: "MCP host" },
];

const ADAPTER_DEFAULTS = {
  akash: {
    entity_id: "pocp-adapt-akash-eco",
    display_name: "Akash Stub (Ecosystem)",
    offers: [{ capability: "llm_inference", adapters: ["akash"] }],
  },
  "render-network": {
    entity_id: "pocp-adapt-render-eco",
    display_name: "Render Stub (Ecosystem)",
    offers: [{ capability: "llm_inference", adapters: ["render-network"] }],
  },
  "io-net": {
    entity_id: "pocp-adapt-ionet-eco",
    display_name: "io.net Stub (Ecosystem)",
    offers: [{ capability: "llm_inference", adapters: ["io-net"] }],
  },
  gensyn: {
    entity_id: "pocp-adapt-gensyn-eco",
    display_name: "Gensyn Stub (Ecosystem)",
    offers: [{ capability: "training", adapters: ["gensyn"] }],
  },
};

function PartnerCard({ partner, fetchJson, authenticated, onSelectEntity, onOutreachLogged }) {
  const declined = partner.declined || partner.partnership_status === "declined";
  return (
    <div className={`mini-card${declined ? " mini-card--muted" : ""}`}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <span className="entity-badge entity-badge--community">partner</span>
        {partner.community_kind && (
          <span className="partner-kind-tag">{partner.community_kind.replace(/_/g, " ")}</span>
        )}
        {partner.outreach_priority && (
          <span className={`partner-priority partner-priority--${partner.outreach_priority}`}>
            {partner.outreach_priority}
          </span>
        )}
      </div>
      <strong style={{ display: "block", marginTop: 8 }}>{partner.display_name || partner.slug}</strong>
      {partner.summary && (
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: "6px 0" }}>{partner.summary}</p>
      )}
      <div className="entity-row__mission">
        Status: {PARTNER_STATUS[partner.partnership_status] || partner.partnership_status || "—"}
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
        {partner.entity_id && (
          <button
            type="button"
            className="btn btn--sm btn--ghost"
            onClick={() => onSelectEntity?.(partner.entity_id)}
          >
            View entity
          </button>
        )}
        {!declined && (
          <LogOutreachForm
            slug={partner.slug}
            currentStatus={partner.partnership_status}
            fetchJson={fetchJson}
            authenticated={authenticated}
            onSuccess={onOutreachLogged}
            compact
          />
        )}
      </div>
    </div>
  );
}

function InspirationCard({ item, onSelectEntity }) {
  const declined = item.declined || item.status === "declined";
  return (
    <div className={`mini-card${declined ? " mini-card--muted" : ""}`}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <span className="entity-badge entity-badge--community">inspiration</span>
        {item.benchmark_tier && <span className="partner-kind-tag">{item.benchmark_tier}</span>}
        {item.status && !declined && <span className="inspiration-tag">{item.status}</span>}
        {declined && <span className="partner-priority partner-priority--high">declined</span>}
      </div>
      <strong style={{ display: "block", marginTop: 8 }}>{item.display_name || item.slug}</strong>
      {item.summary && (
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: "6px 0" }}>{item.summary}</p>
      )}
      {item.mapping_doc && (
        <div className="entity-row__mission" style={{ fontSize: "0.72rem" }}>
          {item.mapping_doc}
        </div>
      )}
      {item.entity_id && (
        <button
          type="button"
          className="btn btn--sm btn--ghost"
          style={{ marginTop: 10 }}
          onClick={() => onSelectEntity?.(item.entity_id)}
        >
          View entity
        </button>
      )}
    </div>
  );
}

function AdapterCard({ adapter, fetchJson, authenticated, setMessage }) {
  const [importing, setImporting] = useState(false);
  const defaults = ADAPTER_DEFAULTS[adapter.slug];

  const handleImport = async () => {
    if (!defaults) return;
    setImporting(true);
    setMessage(null);
    try {
      const result = await fetchJson(`/api/v1/compute/adapters/${adapter.slug}/import`, {
        method: "POST",
        body: JSON.stringify(defaults),
      });
      setMessage(`Imported ${adapter.display_name} → ${result.entity_id}`);
    } catch (err) {
      setMessage(`Import failed: ${err.message}`);
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="mini-card">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <span className="entity-badge entity-badge--community">adapter</span>
        <span className="partner-kind-tag">{adapter.mode}</span>
        {adapter.inspiration_slug && (
          <span className="inspiration-tag">{adapter.inspiration_slug}</span>
        )}
      </div>
      <strong style={{ display: "block", marginTop: 8 }}>{adapter.display_name}</strong>
      <div className="entity-row__mission">
        Network: {adapter.network} · slug: {adapter.slug}
        {adapter.live_wire_active && (
          <span className="partner-priority partner-priority--high" style={{ marginLeft: 6 }}>
            live active
          </span>
        )}
        {adapter.live_configured && !adapter.live_wire_active && (
          <span className="inspiration-tag" style={{ marginLeft: 6 }}>
            live configured
          </span>
        )}
      </div>
      {adapter.note && (
        <p style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: 6 }}>{adapter.note}</p>
      )}
      <p style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: 6 }}>
        External token settlement stays outside PoCP — contribution-bound jobs only.
      </p>
      {authenticated ? (
        <button
          type="button"
          className="btn btn--sm btn--primary"
          style={{ marginTop: 10 }}
          disabled={importing || !defaults}
          onClick={handleImport}
        >
          {importing ? "Importing…" : "Import provider entity"}
        </button>
      ) : (
        <p className="outreach-hint">Dev Login to import adapter providers.</p>
      )}
    </div>
  );
}

export default function EcosystemPanel({ fetchJson, authenticated, onSelectEntity }) {
  const [section, setSection] = useState("partners");
  const [partners, setPartners] = useState([]);
  const [inspirations, setInspirations] = useState([]);
  const [peerEntities, setPeerEntities] = useState([]);
  const [adapters, setAdapters] = useState([]);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(null);
  const [capabilityQuery, setCapabilityQuery] = useState("llm_inference");
  const [discovery, setDiscovery] = useState(null);
  const [discoverLoading, setDiscoverLoading] = useState(false);

  const runDiscover = useCallback(async () => {
    setDiscoverLoading(true);
    setMessage(null);
    try {
      const data = await fetchJson(
        `/api/v1/community-partners/discover?capability=${encodeURIComponent(capabilityQuery)}`
      );
      setDiscovery(data);
    } catch (err) {
      setMessage(err.message);
      setDiscovery(null);
    } finally {
      setDiscoverLoading(false);
    }
  }, [capabilityQuery, fetchJson]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [partnerRes, inspRes, adapterRes, peerRes] = await Promise.all([
        fetchJson("/api/v1/community-partners/partners?include_declined=true"),
        fetchJson("/api/v1/external-inspirations/inspirations?include_declined=true"),
        fetch(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/v1/compute/adapters`).then((r) =>
          r.ok ? r.json() : { adapters: [] }
        ),
        fetchJson("/api/v1/federation/peers/entities").catch(() => ({ entities: [] })),
      ]);
      setPartners(partnerRes.partners || []);
      setInspirations(inspRes.inspirations || []);
      setAdapters(adapterRes.adapters || []);
      setPeerEntities(peerRes.entities || []);
      try {
        const rep = await fetchJson("/api/v1/community-partners/report");
        setReport(rep);
      } catch {
        setReport(null);
      }
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }, [fetchJson]);

  useEffect(() => {
    load();
  }, [load]);

  const sections = [
    { id: "partners", label: "Partners" },
    { id: "inspirations", label: "Inspirations" },
    { id: "discover", label: "Discover" },
    { id: "adapters", label: "Compute adapters" },
  ];

  return (
    <section className="panel">
      <h2 className="panel__title section-heading--ai">Ecosystem Registry</h2>
      <p className="panel__subtitle">
        Community partners · OSS inspiration benchmarks · external compute adapters (no-token-first)
      </p>

      <div className="entity-filters" style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        {sections.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`btn btn--sm${section === s.id ? " btn--primary" : " btn--ghost"}`}
            onClick={() => setSection(s.id)}
          >
            {s.label}
          </button>
        ))}
        <button type="button" className="btn btn--sm btn--secondary" onClick={load} disabled={loading}>
          Refresh
        </button>
      </div>

      {message && <p className="alert alert--info">{message}</p>}
      {loading && <p className="empty-state">Loading ecosystem registry…</p>}

      {!loading && section === "partners" && (
        <>
          {report?.by_status && (
            <div className="partner-discover" style={{ marginBottom: 16 }}>
              {Object.entries(report.by_status).map(([status, count]) => (
                <span key={status} className="partner-kind-tag">
                  {PARTNER_STATUS[status] || status}: {count}
                </span>
              ))}
            </div>
          )}
          <div className="stats-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}>
            {partners.map((p) => (
              <PartnerCard
                key={p.slug}
                partner={p}
                fetchJson={fetchJson}
                authenticated={authenticated}
                onSelectEntity={onSelectEntity}
                onOutreachLogged={load}
              />
            ))}
          </div>
        </>
      )}

      {!loading && section === "inspirations" && (
        <>
          {peerEntities.length > 0 && (
            <>
              <h3 className="panel__subtitle" style={{ marginTop: 0 }}>
                Federation peer nodes
              </h3>
              <div className="stats-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", marginBottom: 20 }}>
                {peerEntities.map((e) => (
                  <div key={e.entity_id || e.id} className="mini-card">
                    <span className="inspiration-tag">{e.is_local ? "LOCAL" : "PEER"}</span>
                    <strong style={{ display: "block", marginTop: 8 }}>{e.name || e.node_id}</strong>
                    {e.trust_weight != null && (
                      <div className="entity-row__mission">Trust: {e.trust_weight}</div>
                    )}
                    <button
                      type="button"
                      className="btn btn--sm btn--ghost"
                      style={{ marginTop: 8 }}
                      onClick={() => onSelectEntity?.(e.entity_id || e.id)}
                    >
                      View entity
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
          <div className="stats-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}>
            {inspirations.map((item) => (
              <InspirationCard key={item.slug} item={item} onSelectEntity={onSelectEntity} />
            ))}
          </div>
        </>
      )}

      {!loading && section === "discover" && (
        <>
          <p className="panel__subtitle" style={{ marginTop: 0 }}>
            Match local compute providers + registry partners for a capability (outreach planning).
          </p>
          <div className="entity-filters" style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            <select
              value={capabilityQuery}
              onChange={(e) => setCapabilityQuery(e.target.value)}
              style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border, #e2e8f0)" }}
            >
              {CAPABILITY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn btn--sm btn--primary"
              onClick={runDiscover}
              disabled={discoverLoading}
            >
              {discoverLoading ? "Searching…" : "Discover partners"}
            </button>
          </div>
          {discovery && (
            <>
              <div className="partner-discover" style={{ marginBottom: 12 }}>
                <span className="partner-kind-tag">
                  Local: {(discovery.local_providers || []).length}
                </span>
                <span className="partner-kind-tag">
                  External: {(discovery.external_partners || []).length}
                </span>
                <span className="partner-kind-tag">
                  Seeking: {(discovery.partners_seeking_this_capability || []).length}
                </span>
              </div>
              {(discovery.local_providers || []).length > 0 && (
                <>
                  <h3 className="panel__subtitle">Local compute providers</h3>
                  <div className="stats-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", marginBottom: 16 }}>
                    {discovery.local_providers.map((p) => (
                      <div key={p.entity_id} className="mini-card">
                        <strong>{p.name}</strong>
                        <div className="entity-row__mission">{p.source}</div>
                        <button
                          type="button"
                          className="btn btn--sm btn--ghost"
                          style={{ marginTop: 8 }}
                          onClick={() => onSelectEntity?.(p.entity_id)}
                        >
                          View entity
                        </button>
                      </div>
                    ))}
                  </div>
                </>
              )}
              {(discovery.external_partners || []).length > 0 && (
                <>
                  <h3 className="panel__subtitle">Registry partners (offer this capability)</h3>
                  <div className="stats-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}>
                    {discovery.external_partners.map((p) => (
                      <PartnerCard
                        key={p.slug}
                        partner={p}
                        fetchJson={fetchJson}
                        authenticated={authenticated}
                        onSelectEntity={onSelectEntity}
                        onOutreachLogged={load}
                      />
                    ))}
                  </div>
                </>
              )}
              {(discovery.external_partners || []).length === 0 &&
                (discovery.local_providers || []).length === 0 && (
                  <p className="empty-state">No matches yet — try another capability or import an adapter provider.</p>
                )}
            </>
          )}
        </>
      )}

      {!loading && section === "adapters" && (
        <>
          <p className="panel__subtitle" style={{ marginTop: 0 }}>
            Stub adapters for Akash, Render, io.net, Gensyn — see docs/COMPUTE-ADAPTER-SPEC.md
          </p>
          <div className="stats-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}>
            {adapters.map((adapter) => (
              <AdapterCard
                key={adapter.slug}
                adapter={adapter}
                fetchJson={fetchJson}
                authenticated={authenticated}
                setMessage={setMessage}
              />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
