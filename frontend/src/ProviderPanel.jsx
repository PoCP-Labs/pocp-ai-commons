import { useCallback, useEffect, useMemo, useState } from "react";

const COMPUTE_CAPABILITIES = [
  { value: "llm_inference", label: "LLM inference" },
  { value: "training", label: "Training" },
  { value: "embeddings", label: "Embeddings" },
  { value: "witness", label: "Witness" },
  { value: "mcp_host", label: "MCP host" },
];

const INTEL_CAPABILITY_TYPES = [
  { value: "general", label: "General" },
  { value: "coding", label: "Coding" },
  { value: "reasoning", label: "Reasoning" },
  { value: "review", label: "Review" },
  { value: "gpu_inference", label: "GPU inference" },
  { value: "gpu_training", label: "GPU training" },
  { value: "tool_call", label: "Tool call" },
  { value: "verification", label: "Verification" },
  { value: "governance", label: "Governance" },
];

const INTEL_UNITS = [
  { value: "skill_invocation", label: "Skill invocation" },
  { value: "agent_run", label: "Agent run" },
  { value: "llm_token", label: "LLM token" },
  { value: "gpu_second", label: "GPU second" },
  { value: "task", label: "Task" },
];

function walletCredits(me) {
  if (!me) return null;
  return me.ai_credits ?? me.wallet?.ai_credits ?? null;
}

export default function ProviderPanel({ fetchJson, me, entities }) {
  const defaultEntityId = me?.entity?.id || "";
  const ownedEntities = useMemo(() => {
    if (!defaultEntityId) return entities || [];
    return (entities || []).filter(
      (e) => e.id === defaultEntityId || e.owner_id === defaultEntityId
    );
  }, [entities, defaultEntityId]);

  const [entityId, setEntityId] = useState(defaultEntityId);
  const [useCustomEntity, setUseCustomEntity] = useState(false);
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [providers, setProviders] = useState([]);
  const [capabilities, setCapabilities] = useState([]);
  const [nodeManifest, setNodeManifest] = useState(null);

  const [computeForm, setComputeForm] = useState({
    capability: "llm_inference",
    adapters: "mock",
    baseUrl: "http://127.0.0.1:8000",
    acceptsPublicJobs: true,
    visibility: "public",
    marketProfileJson: "",
  });

  const [intelForm, setIntelForm] = useState({
    capability_type: "general",
    name: "",
    unit: "skill_invocation",
    base_price: "10",
  });

  useEffect(() => {
    if (defaultEntityId && !useCustomEntity) {
      setEntityId(defaultEntityId);
    }
  }, [defaultEntityId, useCustomEntity]);

  const loadProviders = useCallback(async () => {
    try {
      const data = await fetchJson("/api/v1/compute/providers");
      setProviders(data.providers || []);
    } catch (err) {
      setMessage(err.message);
      setProviders([]);
    }
  }, [fetchJson]);

  const loadCapabilities = useCallback(async () => {
    if (!entityId) {
      setCapabilities([]);
      return;
    }
    try {
      const data = await fetchJson(
        `/api/v1/registry/capabilities?entity_id=${encodeURIComponent(entityId)}`
      );
      setCapabilities(data.items || []);
    } catch (err) {
      setMessage(err.message);
      setCapabilities([]);
    }
  }, [entityId, fetchJson]);

  const loadNodeManifest = useCallback(async () => {
    if (!entityId) {
      setNodeManifest(null);
      return;
    }
    try {
      const data = await fetchJson(`/api/v1/entities/${encodeURIComponent(entityId)}/node-manifest`);
      setNodeManifest(data);
    } catch {
      setNodeManifest(null);
    }
  }, [entityId, fetchJson]);

  const refreshLists = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    try {
      await Promise.all([loadProviders(), loadCapabilities(), loadNodeManifest()]);
    } finally {
      setLoading(false);
    }
  }, [loadProviders, loadCapabilities, loadNodeManifest]);

  useEffect(() => {
    if (me) refreshLists();
  }, [me, refreshLists]);

  const registerCompute = async (e) => {
    e.preventDefault();
    if (!entityId) {
      setMessage("Select or enter an entity ID.");
      return;
    }
    setMessage(null);
    try {
      const body = {
        offers: [
          {
            capability: computeForm.capability,
            adapters: computeForm.adapters
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean),
          },
        ],
        endpoints: { base_url: computeForm.baseUrl.trim() },
        policy: {
          accepts_public_jobs: computeForm.acceptsPublicJobs,
          visibility: computeForm.visibility,
        },
        status: "active",
      };
      if (computeForm.marketProfileJson.trim()) {
        try {
          body.market_profile = JSON.parse(computeForm.marketProfileJson);
        } catch {
          setMessage("Market profile must be valid JSON.");
          return;
        }
      }
      const result = await fetchJson(`/api/v1/compute/entities/${entityId}/register`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setMessage(`Compute profile registered for ${result.entity_id}`);
      await refreshLists();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const sendHeartbeat = async () => {
    if (!entityId) {
      setMessage("Select or enter an entity ID.");
      return;
    }
    setMessage(null);
    try {
      await fetchJson(`/api/v1/compute/entities/${entityId}/heartbeat`, {
        method: "POST",
        body: JSON.stringify({ status: "active" }),
      });
      setMessage(`Heartbeat sent for ${entityId}`);
      await loadProviders();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const registerCapability = async (e) => {
    e.preventDefault();
    if (!entityId) {
      setMessage("Select or enter an entity ID.");
      return;
    }
    if (!intelForm.name.trim()) {
      setMessage("Capability name is required.");
      return;
    }
    setMessage(null);
    try {
      await fetchJson("/api/v1/registry/capabilities", {
        method: "POST",
        body: JSON.stringify({
          entity_id: entityId,
          capability_type: intelForm.capability_type,
          name: intelForm.name.trim(),
          unit: intelForm.unit,
          base_price: parseFloat(intelForm.base_price) || 0,
          price_model: "fixed",
          accepted_units: ["AIC"],
        }),
      });
      setMessage(`Capability "${intelForm.name}" registered.`);
      setIntelForm((f) => ({ ...f, name: "" }));
      await loadCapabilities();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const credits = walletCredits(me);

  if (!me) {
    return (
      <section className="panel">
        <h2 className="panel__title section-heading--ai">Provider Panel</h2>
        <p className="panel__subtitle">Sell compute and capabilities — metered on the PoCP network</p>
        <p className="empty-state">Dev Login to register as a compute or capability provider.</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <h2 className="panel__title section-heading--ai">Provider Panel</h2>
      <p className="panel__subtitle">
        Sell compute and capabilities · earn AI Credits (AIC) when others invoke your offers
      </p>

      {nodeManifest?.facets?.length > 0 && (
        <div className="entity-row__mission" style={{ marginBottom: 12 }}>
          Node facets:{" "}
          {nodeManifest.facets.map((facet) => (
            <span key={facet} className="entity-badge entity-badge--agent" style={{ marginRight: 6 }}>
              {facet.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}

      <div className="profile-card profile-card--wallet" style={{ marginBottom: 16 }}>
        <div className="profile-card__balance">
          Wallet balance:{" "}
          <span className="ai-credits">
            <strong>{credits ?? "—"}</strong>
          </span>{" "}
          AI Credits
        </div>
        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 4 }}>
          Human entity: {me.entity?.name || me.entity?.id}
        </div>
      </div>

      <label className="form-row">
        <span>Provider entity</span>
        {useCustomEntity ? (
          <input
            type="text"
            value={entityId}
            onChange={(e) => setEntityId(e.target.value.trim())}
            placeholder={defaultEntityId || "entity-uuid"}
          />
        ) : (
          <select
            value={entityId}
            onChange={(e) => setEntityId(e.target.value)}
            style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border, #e2e8f0)" }}
          >
            {ownedEntities.length === 0 && defaultEntityId && (
              <option value={defaultEntityId}>{defaultEntityId}</option>
            )}
            {ownedEntities.map((ent) => (
              <option key={ent.id} value={ent.id}>
                {ent.name} ({ent.entity_type})
              </option>
            ))}
          </select>
        )}
      </label>
      <label className="form-row" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
        <input
          type="checkbox"
          checked={useCustomEntity}
          onChange={(e) => setUseCustomEntity(e.target.checked)}
        />
        <span>Use custom entity ID</span>
      </label>

      {message && <p className="alert alert--info">{message}</p>}

      <h3 className="panel__subtitle" style={{ marginTop: 24 }}>
        Offer compute
      </h3>
      <form onSubmit={registerCompute}>
        <label className="form-row">
          <span>Capability offer</span>
          <select
            value={computeForm.capability}
            onChange={(e) => setComputeForm((f) => ({ ...f, capability: e.target.value }))}
            style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border, #e2e8f0)" }}
          >
            {COMPUTE_CAPABILITIES.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="form-row">
          <span>Adapters (comma-separated)</span>
          <input
            type="text"
            value={computeForm.adapters}
            onChange={(e) => setComputeForm((f) => ({ ...f, adapters: e.target.value }))}
            placeholder="mock, ollama"
          />
        </label>
        <label className="form-row">
          <span>Endpoint base URL</span>
          <input
            type="url"
            value={computeForm.baseUrl}
            onChange={(e) => setComputeForm((f) => ({ ...f, baseUrl: e.target.value }))}
            placeholder="http://127.0.0.1:8000"
          />
        </label>
        <label className="form-row">
          <span>Visibility</span>
          <select
            value={computeForm.visibility}
            onChange={(e) => setComputeForm((f) => ({ ...f, visibility: e.target.value }))}
            style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border, #e2e8f0)" }}
          >
            <option value="public">public</option>
            <option value="org_only">org_only</option>
            <option value="private">private</option>
          </select>
        </label>
        <label className="form-row" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          <input
            type="checkbox"
            checked={computeForm.acceptsPublicJobs}
            onChange={(e) => setComputeForm((f) => ({ ...f, acceptsPublicJobs: e.target.checked }))}
          />
          <span>Accepts public jobs</span>
        </label>
        <label className="form-row">
          <span>Market profile overrides (optional JSON)</span>
          <textarea
            className="field-textarea"
            rows={2}
            value={computeForm.marketProfileJson}
            onChange={(e) => setComputeForm((f) => ({ ...f, marketProfileJson: e.target.value }))}
            placeholder='{"base_rate": 1.0}'
          />
        </label>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
          <button type="submit" className="btn btn--primary">
            Register compute profile
          </button>
          <button type="button" className="btn btn--secondary" onClick={sendHeartbeat}>
            Send heartbeat
          </button>
        </div>
      </form>

      <h3 className="panel__subtitle" style={{ marginTop: 24 }}>
        Compute providers
      </h3>
      {loading && <p className="empty-state">Loading providers…</p>}
      {!loading && providers.length === 0 && (
        <p className="empty-state">No active compute providers in the registry.</p>
      )}
      {!loading &&
        providers.map((p) => {
          const profile = p.compute_profile || {};
          const offers = profile.offers || [];
          return (
            <div key={p.entity_id} className="mini-card">
              <strong>{p.name || p.entity_id}</strong>
              <div className="entity-row__mission">
                Status: {profile.status || "—"}
                {offers.length > 0 &&
                  ` · ${offers.map((o) => o.capability || o).join(", ")}`}
              </div>
            </div>
          );
        })}

      <h3 className="panel__subtitle" style={{ marginTop: 32 }}>
        Offer capability
      </h3>
      <form onSubmit={registerCapability}>
        <label className="form-row">
          <span>Capability type</span>
          <select
            value={intelForm.capability_type}
            onChange={(e) => setIntelForm((f) => ({ ...f, capability_type: e.target.value }))}
            style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border, #e2e8f0)" }}
          >
            {INTEL_CAPABILITY_TYPES.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="form-row">
          <span>Name</span>
          <input
            type="text"
            value={intelForm.name}
            onChange={(e) => setIntelForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="My review skill"
          />
        </label>
        <label className="form-row">
          <span>Unit</span>
          <select
            value={intelForm.unit}
            onChange={(e) => setIntelForm((f) => ({ ...f, unit: e.target.value }))}
            style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border, #e2e8f0)" }}
          >
            {INTEL_UNITS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="form-row">
          <span>Base price (fixed · AIC)</span>
          <input
            type="number"
            min="0"
            step="0.01"
            value={intelForm.base_price}
            onChange={(e) => setIntelForm((f) => ({ ...f, base_price: e.target.value }))}
          />
        </label>
        <button type="submit" className="btn btn--primary" style={{ marginTop: 12 }}>
          Register capability
        </button>
      </form>

      <h3 className="panel__subtitle" style={{ marginTop: 24 }}>
        Capabilities for entity
      </h3>
      <div style={{ marginBottom: 12 }}>
        <button type="button" className="btn btn--sm btn--secondary" onClick={refreshLists} disabled={loading}>
          Refresh lists
        </button>
      </div>
      {capabilities.length === 0 && (
        <p className="empty-state">No capabilities registered for this entity yet.</p>
      )}
      {capabilities.map((cap) => (
        <div key={cap.capability_id} className="mini-card mini-card--credits">
          <strong>{cap.name}</strong>
          <div className="entity-row__mission">
            {cap.capability_type} · {cap.unit} · {cap.base_price} AIC ({cap.price_model})
          </div>
        </div>
      ))}
    </section>
  );
}
