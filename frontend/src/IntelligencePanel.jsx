import { useEffect, useState } from "react";



const REGISTER_TYPES = ["tool", "dataset", "workflow", "agent", "skill", "organization", "community"];



function ModuleCard({ module }) {

  const active = module.status === "active";

  return (

    <div className={`stat-block${active ? " stat-block--ai" : ""}`} style={{ borderLeftColor: active ? "var(--ai)" : "var(--text-dim)" }}>

      <div className="stat-block__label">{module.module.replace(/_/g, " ")}</div>

      <div className="stat-block__value" style={{ fontSize: "0.85rem", color: active ? "var(--ai)" : "var(--text-muted)" }}>

        {module.status}

      </div>

      {module.strategy && (

        <div style={{ fontSize: "0.7rem", color: "var(--text-dim)", marginTop: 4 }}>{module.strategy}</div>

      )}

      {module.agent && (

        <div style={{ fontSize: "0.7rem", color: "var(--text-dim)", marginTop: 4 }}>{module.agent}</div>

      )}

    </div>

  );

}



export default function IntelligencePanel({ api, fetchJson, tasks, profile, onSelectEntity }) {

  const [status, setStatus] = useState(null);

  const [protocol, setProtocol] = useState(null);

  const [governance, setGovernance] = useState(null);
  const [stack, setStack] = useState(null);

  const [matchTaskId, setMatchTaskId] = useState(tasks[0]?.id || "");

  const [matchContributionType, setMatchContributionType] = useState("");

  const [matchResult, setMatchResult] = useState(null);

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState(null);



  const [regType, setRegType] = useState("tool");

  const [regName, setRegName] = useState("");

  const [regDescription, setRegDescription] = useState("");

  const [regTags, setRegTags] = useState("");

  const [regResult, setRegResult] = useState(null);

  const [regLoading, setRegLoading] = useState(false);

  const [computeEntityId, setComputeEntityId] = useState("");
  const [computeCapability, setComputeCapability] = useState("witness");
  const [computeBaseUrl, setComputeBaseUrl] = useState("");
  const [computeProviders, setComputeProviders] = useState(null);
  const [computeJobResult, setComputeJobResult] = useState(null);
  const [computeLoading, setComputeLoading] = useState(false);

  useEffect(() => {
    setError(null);

    Promise.all([

      fetch(`${api}/api/v1/intelligence/status`).then((r) => r.json()),

      fetch(`${api}/api/v1/intelligence/protocol`).then((r) => r.json()),

      fetch(`${api}/api/v1/intelligence/governance/summary`).then((r) => r.json()),

      fetch(`${api}/api/v1/intelligence/protocol/stack`).then((r) => r.json()),

    ])

      .then(([s, p, g, st]) => {

        setStatus(s);

        setProtocol(p);

        setGovernance(g);

        setStack(st);

      })

      .catch((err) => setError(err.message));

  }, [api]);

  useEffect(() => {
    if (profile?.entity_id && !computeEntityId) {
      setComputeEntityId(profile.entity_id);
    }
  }, [profile, computeEntityId]);

  const loadComputeProviders = async () => {
    setComputeLoading(true);
    setError(null);
    try {
      const data = await fetch(`${api}/api/v1/compute/providers`).then((r) => r.json());
      setComputeProviders(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setComputeLoading(false);
    }
  };

  const registerComputeProfile = async (e) => {
    e.preventDefault();
    if (!profile || !computeEntityId.trim()) return;
    setComputeLoading(true);
    setError(null);
    try {
      await fetchJson(`/api/v1/intelligence/entities/${computeEntityId.trim()}/compute/register`, {
        method: "POST",
        body: JSON.stringify({
          offers: [{ capability: computeCapability, adapters: ["ollama", "mock"] }],
          endpoints: { base_url: computeBaseUrl.trim() || api.replace(/\/$/, "") },
          status: "active",
        }),
      });
      await loadComputeProviders();
    } catch (err) {
      setError(err.message);
    } finally {
      setComputeLoading(false);
    }
  };

  const runComputeJob = async () => {
    if (!profile) return;
    setComputeLoading(true);
    setError(null);
    try {
      const result = await fetchJson("/api/v1/compute/jobs", {
        method: "POST",
        body: JSON.stringify({
          capability: computeCapability,
          constraints: { input_preview: "capability panel test" },
        }),
      });
      setComputeJobResult(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setComputeLoading(false);
    }
  };

  useEffect(() => {

    if (tasks.length && !matchTaskId) setMatchTaskId(tasks[0].id);

  }, [tasks, matchTaskId]);



  const runMatch = async () => {

    if (!profile) return;

    setLoading(true);

    setError(null);

    try {

      const result = await fetchJson("/api/v1/intelligence/match", {

        method: "POST",

        body: JSON.stringify({

          task_id: matchTaskId || null,

          contribution_type: matchContributionType || null,

          limit: 5,

        }),

      });

      setMatchResult(result);

    } catch (err) {

      setError(err.message);

    } finally {

      setLoading(false);

    }

  };



  const registerEntity = async (e) => {

    e.preventDefault();

    if (!profile || !regName.trim()) return;

    setRegLoading(true);

    setError(null);

    setRegResult(null);

    try {

      const tags = regTags

        .split(",")

        .map((t) => t.trim())

        .filter(Boolean);

      const result = await fetchJson("/api/v1/intelligence/entities/register", {

        method: "POST",

        body: JSON.stringify({

          entity_type: regType,

          name: regName.trim(),

          description: regDescription.trim() || null,

          tags,

          capabilities: tags,

        }),

      });

      setRegResult(result);

      setRegName("");

      setRegDescription("");

      setRegTags("");

      onSelectEntity?.(result.entity?.id);

    } catch (err) {

      setError(err.message);

    } finally {

      setRegLoading(false);

    }

  };



  return (

    <>

      {stack && (

        <section className="panel panel--protocol-stack">

          <h2 className="panel__title">Protocol Stack</h2>

          <p className="panel__subtitle">{stack.north_star}</p>

          <div className="protocol-stack-layers">

            {stack.layers?.map((layer) => (

              <div

                key={layer.id}

                className={`stat-block${layer.build_here ? " stat-block--ai" : ""}`}

                style={{

                  borderLeftColor: layer.build_here ? "var(--ai)" : "var(--text-dim)",

                  opacity: layer.build_here ? 1 : 0.75,

                }}

              >

                <div className="stat-block__label">

                  {layer.name}

                  {layer.build_here ? " · build focus" : " · thin binding"}

                </div>

                <ul style={{ fontSize: "0.75rem", color: "var(--text-muted)", margin: "8px 0 0", paddingLeft: 18 }}>

                  {(layer.owns || []).slice(0, 5).map((item) => (

                    <li key={item}>{item}</li>

                  ))}

                </ul>

              </div>

            ))}

          </div>

        </section>

      )}

      <section className="panel">

        <h2 className="panel__title section-heading--ai">Capability Layer</h2>

        <p className="panel__subtitle">

          {protocol?.principle || "Everything connects through verified contribution."}

        </p>

        {protocol && (

          <div className="loop-strip" style={{ marginBottom: 12 }}>

            <span className="loop-strip__step--active">Protocol v{protocol.protocol_version}</span>

            <span className="loop-strip__arrow"> · </span>

            <span>Layer v{protocol.capability_layer_version}</span>

            <span className="loop-strip__arrow"> · </span>

            <span>{protocol.entity_types?.length} entity types</span>

          </div>

        )}

        {error && !status && <div className="alert alert--error">{error}</div>}

        {status && (

          <div className="stats-grid">

            <div className="stat-block stat-block--ai">

              <div className="stat-block__label">Modules Active</div>

              <div className="stat-block__value stat-block__value--ai">

                {status.modules_active}/{status.modules_total}

              </div>

            </div>

            <div className="stat-block">

              <div className="stat-block__label">Principle</div>

              <div className="stat-block__value" style={{ fontSize: "0.75rem" }}>

                {status.principle}

              </div>

            </div>

          </div>

        )}

        {status?.modules && (

          <div className="stats-grid">

            {status.modules.map((m) => (

              <ModuleCard key={m.module} module={m} />

            ))}

          </div>

        )}

      </section>



      {governance && (

        <section className="panel">

          <h2 className="panel__title">Governance Assistant</h2>

          <p className="panel__subtitle">Entity-equal automation — policy defines finalization</p>

          <div className="stats-grid">

            <div className="stat-block">

              <div className="stat-block__label">Pending Finalization</div>

              <div className="stat-block__value stat-block__value--btc">

                {governance.network_snapshot?.contributions_pending_finalization
                  ?? governance.network_snapshot?.contributions_pending_human_review
                  ?? 0}

              </div>

            </div>

            <div className="stat-block stat-block--ai">

              <div className="stat-block__label">Ledger Blocks</div>

              <div className="stat-block__value stat-block__value--ai">

                {governance.network_snapshot?.ledger_blocks ?? 0}

              </div>

            </div>

          </div>

          {governance.observations?.length > 0 && (

            <div style={{ marginTop: 12 }}>

              {governance.observations.map((obs) => (

                <div key={obs} className="alert alert--info" style={{ marginBottom: 8 }}>

                  {obs}

                </div>

              ))}

            </div>

          )}

        </section>

      )}



      <section className="panel">

        <h2 className="panel__title section-heading--ai">Register Entity</h2>

        <p className="panel__subtitle">Universal registration — Tool, Dataset, Workflow, Agent, Skill, and more</p>

        {!profile ? (

          <p className="empty-state">Dev Login to register contribution-capable entities.</p>

        ) : (

          <form onSubmit={registerEntity} className="form-stack">

            <label className="field-label">

              Entity type

              <select className="field-select" value={regType} onChange={(e) => setRegType(e.target.value)}>

                {REGISTER_TYPES.map((t) => (

                  <option key={t} value={t}>

                    {t}

                  </option>

                ))}

              </select>

            </label>

            <label className="field-label">

              Name

              <input

                className="field-input"

                value={regName}

                onChange={(e) => setRegName(e.target.value)}

                placeholder="e.g. R Study Helper Tool"

                required

              />

            </label>

            <label className="field-label">

              Description

              <textarea

                className="field-textarea"

                value={regDescription}

                onChange={(e) => setRegDescription(e.target.value)}

                rows={2}

                placeholder="What does this entity contribute?"

              />

            </label>

            <label className="field-label">

              Tags (comma-separated)

              <input

                className="field-input"

                value={regTags}

                onChange={(e) => setRegTags(e.target.value)}

                placeholder="r, study, language"

              />

            </label>

            <button type="submit" className="btn btn--ai" disabled={regLoading || !regName.trim()}>

              {regLoading ? "Registering…" : "Register via Capability Layer"}

            </button>

            {regResult && (

              <div className="alert alert--success" style={{ marginTop: 12 }}>

                Registered <strong>{regResult.entity?.name}</strong> ({regResult.entity?.entity_type}) —{" "}

                <button

                  type="button"

                  className="btn btn--ghost"

                  style={{ padding: 0, border: "none", color: "var(--ai)" }}

                  onClick={() => onSelectEntity?.(regResult.entity?.id)}

                >

                  view entity

                </button>

              </div>

            )}

          </form>

        )}

      </section>

      <section className="panel">
        <h2 className="panel__title section-heading--ai">Distributed Compute Mesh</h2>
        <p className="panel__subtitle">Entity ComputeProfile · provider discovery · advisory job scheduling</p>
        {!profile ? (
          <p className="empty-state">Dev Login to register compute providers.</p>
        ) : (
          <>
            <button type="button" className="btn btn--ghost" onClick={loadComputeProviders} disabled={computeLoading}>
              Refresh providers
            </button>
            {computeProviders && (
              <p style={{ fontSize: "0.8rem", color: "var(--text-dim)", marginTop: 8 }}>
                {computeProviders.provider_count} active provider{computeProviders.provider_count === 1 ? "" : "s"}
              </p>
            )}
            <form onSubmit={registerComputeProfile} className="form-stack" style={{ marginTop: 12 }}>
              <label className="field-label">
                Entity ID
                <input className="field-input" value={computeEntityId} onChange={(e) => setComputeEntityId(e.target.value)} />
              </label>
              <label className="field-label">
                Capability
                <select className="field-select" value={computeCapability} onChange={(e) => setComputeCapability(e.target.value)}>
                  <option value="witness">witness</option>
                  <option value="llm_inference">llm_inference</option>
                  <option value="mcp_host">mcp_host</option>
                </select>
              </label>
              <label className="field-label">
                Base URL
                <input className="field-input" value={computeBaseUrl} onChange={(e) => setComputeBaseUrl(e.target.value)} placeholder={api} />
              </label>
              <button type="submit" className="btn btn--ai" disabled={computeLoading}>
                Register ComputeProfile
              </button>
            </form>
            <button type="button" className="btn btn--ai" style={{ marginTop: 12 }} onClick={runComputeJob} disabled={computeLoading}>
              Schedule test job
            </button>
            {computeJobResult && (
              <div className="alert alert--info" style={{ marginTop: 12, fontSize: "0.8rem" }}>
                Job {computeJobResult.job_id} → {computeJobResult.selected_provider?.source}
              </div>
            )}
          </>
        )}
      </section>

      <section className="panel">

        <h2 className="panel__title section-heading--ai">Skill / Agent Matching</h2>

        <p className="panel__subtitle">v0.3 — reputation + semantic fit + invocation history (advisory)</p>

        {!profile ? (

          <p className="empty-state">Dev Login to run capability matching.</p>

        ) : (

          <>

            {tasks.length > 0 && (

              <label className="field-label">

                Task context

                <select className="field-select" value={matchTaskId} onChange={(e) => setMatchTaskId(e.target.value)}>

                  {tasks.map((t) => (

                    <option key={t.id} value={t.id}>

                      {t.title}

                    </option>

                  ))}

                </select>

              </label>

            )}

            <label className="field-label">

              Contribution type (optional)

              <input

                className="field-input"

                value={matchContributionType}

                onChange={(e) => setMatchContributionType(e.target.value)}

                placeholder="e.g. code_contribution, documentation"

              />

            </label>

            <button type="button" className="btn btn--ai" onClick={runMatch} disabled={loading}>

              {loading ? "Matching…" : "Run Match Engine"}

            </button>

            {matchResult && (

              <div style={{ marginTop: 16 }}>

                <p style={{ fontSize: "0.8rem", color: "var(--text-dim)" }}>

                  Strategy: {matchResult.strategy}

                  {matchResult.task_keywords?.length > 0 && (

                    <> · keywords: {matchResult.task_keywords.join(", ")}</>

                  )}

                </p>

                <h3 style={{ fontSize: "0.85rem", color: "var(--violet)", marginTop: 12 }}>Agents</h3>

                {matchResult.recommended_agents?.map((a) => (

                  <div key={a.entity_id} className="mini-card mini-card--rep">

                    <button

                      type="button"

                      className="btn btn--ghost"

                      style={{ padding: 0, border: "none", color: "inherit", cursor: "pointer" }}

                      onClick={() => onSelectEntity?.(a.entity_id)}

                    >

                      <strong>{a.name}</strong>

                    </button>{" "}

                    · score {a.match_score} · rep {a.reputation} · sem {a.semantic_fit}

                  </div>

                ))}

                <h3 style={{ fontSize: "0.85rem", color: "var(--green)", marginTop: 12 }}>Skills</h3>

                {matchResult.recommended_skills?.map((s) => (

                  <div key={s.entity_id} className="mini-card mini-card--credits">

                    <button

                      type="button"

                      className="btn btn--ghost"

                      style={{ padding: 0, border: "none", color: "inherit", cursor: "pointer" }}

                      onClick={() => onSelectEntity?.(s.entity_id)}

                    >

                      <strong>{s.name}</strong>

                    </button>{" "}

                    · score {s.match_score} · sem {s.semantic_fit}

                    {s.tags?.length > 0 && <> · tags: {s.tags.join(", ")}</>}

                  </div>

                ))}

                {matchResult.recommended_compute_providers?.length > 0 && (
                  <>
                    <h3 style={{ fontSize: "0.85rem", color: "var(--amber)", marginTop: 12 }}>Compute</h3>
                    {matchResult.recommended_compute_providers.map((p) => (
                      <div key={`${p.entity_id}-${p.capability}`} className="mini-card mini-card--compute">
                        <button
                          type="button"
                          className="btn btn--ghost"
                          style={{ padding: 0, border: "none", color: "inherit", cursor: "pointer" }}
                          onClick={() => onSelectEntity?.(p.entity_id)}
                        >
                          <strong>{p.name}</strong>
                        </button>{" "}
                        · {p.capability} · score {p.match_score}
                        {p.compute_provider_reputation > 0 && <> · rep {p.compute_provider_reputation}</>}
                        {p.region && <> · {p.region}</>}
                      </div>
                    ))}
                  </>
                )}

              </div>

            )}

          </>

        )}

      </section>

      {error && status && <div className="alert alert--error">{error}</div>}

    </>

  );

}

