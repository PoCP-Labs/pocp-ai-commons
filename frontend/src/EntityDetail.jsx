import { useCallback, useEffect, useState } from "react";
import ComputeAttributionPanel from "./ComputeAttributionPanel";
import EntityWalletActivity from "./EntityWalletActivity";
import LogOutreachForm from "./LogOutreachForm";
function ContributionReceiptSummary({ contributionId, entityMap, fetchJson, onSelectEntity }) {
  const [proof, setProof] = useState(null);
  const [computeJobs, setComputeJobs] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!expanded || !fetchJson || !contributionId) return;
    let cancelled = false;
    setLoading(true);
    Promise.all([
      fetchJson(`/api/v1/contributions/${contributionId}/proof`).catch(() => null),
      fetchJson(`/api/v1/contributions/${contributionId}/compute-jobs`).catch(() => null),
    ])
      .then(([proofData, jobsData]) => {
        if (cancelled) return;
        setProof(proofData);
        setComputeJobs(jobsData);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [expanded, contributionId, fetchJson]);

  const hasReceipts =
    (proof?.compute_attribution?.receipt_count || 0) > 0 || (computeJobs?.job_count || 0) > 0;

  return (
    <div style={{ marginTop: 8 }}>
      <button
        type="button"
        className="btn btn--ghost btn--sm"
        onClick={() => setExpanded((v) => !v)}
      >
        {expanded ? "Hide compute receipts" : "Show compute receipts"}
      </button>
      {expanded && loading && (
        <p className="proof-layers__meta" style={{ marginTop: 6 }}>
          Loading proof…
        </p>
      )}
      {expanded && !loading && !hasReceipts && (
        <p className="proof-layers__meta" style={{ marginTop: 6 }}>
          No compute receipts bound to this contribution.
        </p>
      )}
      {expanded && !loading && hasReceipts && (
        <ComputeAttributionPanel
          computeAttribution={proof?.compute_attribution}
          computeJobs={computeJobs}
          entityMap={entityMap}
          onSelectEntity={onSelectEntity}
        />
      )}
    </div>
  );
}

export default function EntityDetail({
  entity,
  wallet,
  reputationRows,
  contributions,
  entityMap,
  onBack,
  fetchJson,
  authenticated = false,
  onSelectEntity,
  onOpenContribution,
  onOpenLedger,
}) {
  const [audit, setAudit] = useState([]);
  const [portable, setPortable] = useState(null);
  const [ontologySlice, setOntologySlice] = useState(null);
  const [agentRep, setAgentRep] = useState(null);
  const [inspirationDetail, setInspirationDetail] = useState(null);
  const [federationImports, setFederationImports] = useState(null);
  const [partnerDetail, setPartnerDetail] = useState(null);
  const [partnerOutreachLog, setPartnerOutreachLog] = useState([]);
  const [nodeManifest, setNodeManifest] = useState(null);
  const [localChain, setLocalChain] = useState(null);

  const isPartnerEntity =
    entity?.metadata?.roles?.includes("community_partner") ||
    entity?.metadata?.partner_slug;

  const loadPartnerData = useCallback(() => {
    if (!fetchJson || !entity?.id || !isPartnerEntity) return Promise.resolve();
    const slug = entity.metadata?.partner_slug;
    const profilePromise = fetchJson(`/api/v1/community-partners/entities/${entity.id}`)
      .then((data) => {
        setPartnerDetail(data);
      })
      .catch(() => {
        setPartnerDetail(null);
      });
    const logPromise = slug
      ? fetchJson(`/api/v1/community-partners/partners/${slug}/outreach-log`)
          .then((data) => {
            setPartnerOutreachLog(data.entries || []);
          })
          .catch(() => {
            setPartnerOutreachLog([]);
          })
      : Promise.resolve();
    return Promise.all([profilePromise, logPromise]);
  }, [entity?.id, entity?.metadata?.partner_slug, fetchJson, isPartnerEntity]);

  const isInspirationEntity =
    entity?.entity_type === "community" &&
    (entity?.metadata?.roles?.includes("external_inspiration") ||
      entity?.id?.startsWith("pocp-insp-") || entity?.id?.startsWith("pocp-entity-inspiration-"));
  const isFederationPeer =
    entity?.entity_type === "community" &&
    (entity?.metadata?.roles?.includes("federation_peer") ||
      entity?.metadata?.roles?.includes("federation_node") ||
      entity?.id?.startsWith("pocp-entity-federation-"));

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

    fetchJson(`/api/v1/entities/${entity.id}/ontology`)
      .then((data) => {
        if (!cancelled) setOntologySlice(data);
      })
      .catch(() => {
        if (!cancelled) setOntologySlice(null);
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

    if (isInspirationEntity) {
      fetchJson(`/api/v1/external-inspirations/entities/${entity.id}`)
        .then((data) => {
          if (!cancelled) setInspirationDetail(data);
        })
        .catch(() => {
          if (!cancelled) setInspirationDetail(null);
        });
    } else {
      setInspirationDetail(null);
    }

    fetchJson(`/api/v1/federation/entities/${entity.id}/imports?limit=8`)
      .then((data) => {
        if (!cancelled) setFederationImports(data);
      })
      .catch(() => {
        if (!cancelled) setFederationImports(null);
      });

    fetchJson(`/api/v1/entities/${entity.id}/node-manifest`)
      .then((data) => {
        if (!cancelled) setNodeManifest(data);
      })
      .catch(() => {
        if (!cancelled) setNodeManifest(null);
      });

    fetchJson(`/api/v1/entities/${entity.id}/local-chain?limit=8`)
      .then((data) => {
        if (!cancelled) setLocalChain(data);
      })
      .catch(() => {
        if (!cancelled) setLocalChain(null);
      });

    if (isPartnerEntity) {
      loadPartnerData();
    } else {
      setPartnerDetail(null);
      setPartnerOutreachLog([]);
    }

    return () => {
      cancelled = true;
    };
  }, [entity?.id, entity?.entity_type, entity?.metadata?.roles, fetchJson, isInspirationEntity, isPartnerEntity, loadPartnerData]);

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
          {entity.metadata?.github_url && (
            <div className="entity-row__mission" style={{ marginTop: 8 }}>
              <a href={entity.metadata.github_url} target="_blank" rel="noreferrer">
                {entity.metadata.github_url}
              </a>
            </div>
          )}
          {entity.metadata?.inspiration_status && (
            <div className="entity-row__mission" style={{ marginTop: 8 }}>
              Relationship: {entity.metadata.inspiration_status.replace(/_/g, " ")}
            </div>
          )}
          {isFederationPeer && entity.metadata?.node_id && (
            <div className="entity-row__mission" style={{ marginTop: 8 }}>
              Node ID: {entity.metadata.node_id}
              {entity.metadata.trust_weight != null ? ` · trust ${entity.metadata.trust_weight}` : ""}
            </div>
          )}
          {isFederationPeer && entity.metadata?.base_url && (
            <div className="entity-row__mission">{entity.metadata.base_url}</div>
          )}
          {entity.metadata?.decline_reason && (
            <div className="entity-row__mission" style={{ marginTop: 8, color: "var(--text-dim)" }}>
              {entity.metadata.decline_reason}
            </div>
          )}
        </div>

        {fetchJson ? (
          <EntityWalletActivity
            entityId={entity.id}
            fetchJson={fetchJson}
            onOpenContribution={onOpenContribution}
            onOpenLedger={onOpenLedger}
          />
        ) : wallet ? (
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
        ) : null}      </div>

      {entity.metadata?.roles?.length > 0 && (
        <div className="entity-row__mission" style={{ marginBottom: 12 }}>
          Roles: {entity.metadata.roles.join(", ")}
        </div>
      )}

      {nodeManifest?.facets?.length > 0 && (
        <div className="mini-card" style={{ marginBottom: 12 }}>
          <strong>Node facets</strong>
          <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6 }}>
            {nodeManifest.facets.map((facet) => (
              <span key={facet} className="entity-badge entity-badge--agent">
                {facet.replace(/_/g, " ")}
              </span>
            ))}
          </div>
          {(nodeManifest.capabilities || []).length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: "0.8rem", fontWeight: 600, marginBottom: 6 }}>Published capabilities</div>
              {nodeManifest.capabilities.slice(0, 8).map((cap) => (
                <div key={cap.capability_id || cap.capability_type} className="entity-row__mission">
                  {cap.name} · {cap.capability_type} · {cap.unit}
                  {cap.exchange_kind ? ` · ${cap.exchange_kind}` : ""}
                  {cap.base_price != null ? ` · ${cap.base_price} AIC` : ""}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {localChain?.records?.length > 0 && (
        <div className="mini-card" style={{ marginBottom: 12 }}>
          <strong>Exchange activity (ELC)</strong>
          <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: 4 }}>
            {localChain.total} settlement(s) · head {localChain.head_hash?.slice(0, 12)}…
          </div>
          {localChain.records.slice().reverse().map((row) => (
            <div key={row.seq} className="entity-row__mission" style={{ marginTop: 6 }}>
              #{row.seq} {row.exchange_kind || "exchange"} · {row.ref_id?.slice(0, 16)}…
              {row.usage?.bc_debited != null ? ` · −${row.usage.bc_debited} BC` : ""}
              {row.usage?.bc_credited != null ? ` · +${row.usage.bc_credited} BC` : ""}
              {authenticated && fetchJson && (
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  style={{ marginLeft: 8 }}
                  title="Publish as contribution (requires open task)"
                  onClick={() => {
                    const taskId = window.prompt("Task ID to attach contribution to:");
                    if (!taskId?.trim()) return;
                    const desc = window.prompt("Short description (optional):") || undefined;
                    fetchJson(`/api/v1/exchanges/${row.ref_id}/publish-contribution`, {
                      method: "POST",
                      body: JSON.stringify({
                        task_id: taskId.trim(),
                        description: desc,
                      }),
                    })
                      .then((c) => window.alert(`Contribution submitted: ${c.id}`))
                      .catch((err) => window.alert(err.message || "Publish failed"));
                  }}
                >
                  发布为贡献
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {ontologySlice?.ontology && (
        <div className="mini-card" style={{ marginBottom: 12 }}>
          <strong>Entity ontology</strong>
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: 6 }}>
            {ontologySlice.ontology.type_spec?.description ||
              ontologySlice.ontology.type_spec?.description_zh}
          </div>
          {(ontologySlice.ontology.typical_roles || []).length > 0 && (
            <div style={{ fontSize: "0.75rem", marginTop: 6 }}>
              Typical roles: {ontologySlice.ontology.typical_roles.join(", ")}
            </div>
          )}
          {ontologySlice.ontology.accountable_principal && (
            <div style={{ fontSize: "0.75rem", marginTop: 4, color: "var(--btc)" }}>
              Accountability anchor
            </div>
          )}
        </div>
      )}

      {inspirationDetail && (
        <>
          <h3 style={{ fontSize: "0.9rem", marginBottom: 8 }}>Borrowed Contributions to PoCP</h3>
          {(inspirationDetail.recorded_contributions || inspirationDetail.contributions || []).map((c) => (
            <div key={c.contribution_id || c.id} className="mini-card">
              <strong>{c.title}</strong>
              {(c.pocp_modules || []).length > 0 && (
                <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: 4 }}>
                  Modules: {(c.pocp_modules || []).slice(0, 3).join(", ")}
                  {(c.pocp_modules || []).length > 3 ? "…" : ""}
                </div>
              )}
              {(c.api_paths || []).length > 0 && (
                <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: 4 }}>
                  APIs: {(c.api_paths || []).slice(0, 2).join(" · ")}
                </div>
              )}
            </div>
          ))}
        </>
      )}

      {partnerDetail && (
        <>
          <h3 style={{ fontSize: "0.9rem", marginBottom: 8 }}>Community Partnership</h3>
          <div className="mini-card">
            Status: <strong>{partnerDetail.partnership_status?.replace(/_/g, " ") || "—"}</strong>
            {partnerDetail.community_kind && (
              <span> · {partnerDetail.community_kind.replace(/_/g, " ")}</span>
            )}
            {(partnerDetail.alignment || []).length > 0 && (
              <div style={{ fontSize: "0.75rem", marginTop: 6 }}>
                Alignment: {partnerDetail.alignment.join(", ")}
              </div>
            )}
            {(partnerDetail.capabilities_offered || []).length > 0 && (
              <div style={{ fontSize: "0.75rem", marginTop: 6 }}>
                Offers:{" "}
                {(partnerDetail.capabilities_offered || [])
                  .map((c) => `${c.capability}${c.label ? ` (${c.label})` : ""}`)
                  .join(" · ")}
              </div>
            )}
            {(partnerDetail.capabilities_sought || []).length > 0 && (
              <div style={{ fontSize: "0.75rem", marginTop: 4, color: "var(--text-dim)" }}>
                Seeks:{" "}
                {(partnerDetail.capabilities_sought || [])
                  .map((c) => `${c.capability}${c.label ? ` (${c.label})` : ""}`)
                  .join(" · ")}
              </div>
            )}
            {partnerDetail.outreach?.next_action && (
              <div style={{ fontSize: "0.75rem", marginTop: 6, color: "var(--ai)" }}>
                Next outreach: {partnerDetail.outreach.next_action}
              </div>
            )}
          </div>
          <div style={{ marginTop: 10 }}>
            <LogOutreachForm
              slug={partnerDetail.slug || entity.metadata?.partner_slug}
              currentStatus={partnerDetail.partnership_status}
              fetchJson={fetchJson}
              authenticated={authenticated}
              onSuccess={loadPartnerData}
            />
          </div>
          {partnerOutreachLog.length > 0 && (
            <>
              <h4 style={{ fontSize: "0.82rem", margin: "12px 0 6px" }}>Outreach Log</h4>
              {partnerOutreachLog.slice(0, 5).map((entry, idx) => (
                <div key={`${entry.at}-${idx}`} className="mini-card">
                  <strong>{entry.event_type?.replace(/_/g, " ")}</strong>
                  {entry.notes && (
                    <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: 4 }}>{entry.notes}</div>
                  )}
                  <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 4 }}>{entry.at}</div>
                </div>
              ))}
            </>
          )}
        </>
      )}

      {federationImports &&
        (federationImports.received_count > 0 || federationImports.exported_count > 0) && (
          <>
            {federationImports.received_count > 0 && (
              <>
                <h3 style={{ fontSize: "0.9rem", margin: "16px 0 8px" }}>Federated Imports Received</h3>
                {federationImports.received_imports.map((item) => (
                  <div key={item.id} className="mini-card">
                    <strong>{item.task_title}</strong>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: 4 }}>
                      From {item.peer_entity_name || item.source_node_id} · rep +{item.reputation_applied}
                    </div>
                  </div>
                ))}
              </>
            )}
            {federationImports.exported_count > 0 && (
              <>
                <h3 style={{ fontSize: "0.9rem", margin: "16px 0 8px" }}>Contributions Exported via Federation</h3>
                {federationImports.exported_imports.map((item) => (
                  <div key={item.id} className="mini-card">
                    <strong>{item.task_title}</strong>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: 4 }}>
                      Imported locally for {item.primary_entity_name || item.primary_portable_id}
                    </div>
                  </div>
                ))}
              </>
            )}
          </>
        )}

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
              {fetchJson && (
                <ContributionReceiptSummary
                  contributionId={c.id}
                  entityMap={entityMap}
                  fetchJson={fetchJson}
                  onSelectEntity={onSelectEntity}
                />
              )}
            </div>
          ))}
        </>
      )}
    </section>
  );
}
