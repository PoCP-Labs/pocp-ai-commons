import { useEffect, useState } from "react";

export default function ContributionInsights({
  contributionId,
  fetchJson,
  currentEntityId,
  reviewerId,
  onAction,
}) {
  const [clarion, setClarion] = useState(null);
  const [advisory, setAdvisory] = useState(null);
  const [attribution, setAttribution] = useState(null);
  const [inspirations, setInspirations] = useState(null);
  const [partners, setPartners] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    if (!contributionId || !fetchJson) return;
    let cancelled = false;
    setLoading(true);
    Promise.all([
      fetchJson(`/api/v1/contributions/${contributionId}/clarion-review`).catch(() => null),
      fetchJson(`/api/v1/contributions/${contributionId}/reward-advisory`).catch(() => null),
      fetchJson(`/api/v1/contributions/${contributionId}/attribution-proof`).catch(() => null),
      fetchJson(`/api/v1/contributions/${contributionId}/external-inspirations`).catch(() => null),
      fetchJson(`/api/v1/contributions/${contributionId}/community-partners`).catch(() => null),
    ])
      .then(([clarionPacket, rewardPacket, attributionProof, inspirationPacket, partnerPacket]) => {
        if (cancelled) return;
        setClarion(clarionPacket);
        setAdvisory(rewardPacket);
        setAttribution(attributionProof);
        setInspirations(inspirationPacket);
        setPartners(partnerPacket);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [contributionId, fetchJson]);

  async function runAction(action) {
    if (!contributionId || !reviewerId) return;
    setMessage(null);
    try {
      const path =
        action === "approve"
          ? `/api/v1/contributions/${contributionId}/approve`
          : action === "reject"
            ? `/api/v1/contributions/${contributionId}/reject`
            : `/api/v1/contributions/${contributionId}/request-changes`;
      await fetchJson(path, {
        method: "POST",
        body: JSON.stringify({
          reviewer_id: reviewerId,
          feedback:
            action === "approve"
              ? "Approved (traceable finalization)."
              : action === "reject"
                ? "Rejected (traceable finalization)."
                : "Please revise and resubmit.",
        }),
      });
      setMessage(`${action} recorded.`);
      onAction?.();
    } catch (err) {
      setMessage(err.message || "Action failed");
    }
  }

  if (!contributionId) return null;

  return (
    <div className="insights-panel">
      <h3 style={{ fontSize: "0.9rem", margin: "0 0 8px", color: "var(--ai)" }}>Clarion-0 Unified Review</h3>
      {loading && <p className="empty-state">Loading advisory packet…</p>}
      {!loading && clarion && (
        <>
          <div className="mini-card">
            Recommended: <strong>{clarion.proof_draft?.recommended_status || "needs review"}</strong>
            {" · "}
            Avg score: <strong>{clarion.rubric?.avg_score ?? "—"}</strong>
            {" · "}
            Risk: <strong>{clarion.rubric?.risk_score ?? "—"}</strong>
          </div>
          {clarion.suggested_rewards && (
            <div className="mini-card" style={{ marginTop: 8 }}>
              Suggested CP: <strong>{clarion.suggested_rewards.cp ?? "—"}</strong>
              {" · "}
              AI Credits: <strong>{clarion.suggested_rewards.ai_credits ?? "—"}</strong>
            </div>
          )}
          {clarion.concerns?.length > 0 && (
            <ul style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 8 }}>
              {clarion.concerns.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </>
      )}

      {advisory?.recommended && (
        <div className="mini-card" style={{ marginTop: 8 }}>
          AI consensus pass: <strong>{String(advisory.recommended.passed ?? "—")}</strong>
        </div>
      )}

      {attribution?.merkle_root && (
        <div className="mini-card" style={{ marginTop: 8 }}>
          Attribution Merkle root: <code>{attribution.merkle_root.slice(0, 16)}…</code>
          {" · "}
          Builders: <strong>{attribution.leaf_count ?? 0}</strong>
        </div>
      )}

      {inspirations?.matched_count > 0 && (
        <>
          <h4 style={{ fontSize: "0.82rem", margin: "12px 0 6px", color: "#fb7185" }}>
            External Inspiration Patterns
          </h4>
          {(inspirations.inspirations || []).map((item) => (
            <div key={item.slug || item.entity_id} className="mini-card">
              <span className="entity-badge entity-badge--community">community</span>
              {" "}
              <strong>{item.display_name || item.slug}</strong>
              {(item.contributions || []).slice(0, 2).map((c) => (
                <div key={c.contribution_id} style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: 4 }}>
                  {c.title}
                  {c.matched_module ? ` · ${c.matched_module}` : ""}
                </div>
              ))}
            </div>
          ))}
        </>
      )}

      {partners && (partners.matched_partners?.length > 0 || partners.high_priority_outreach?.length > 0) && (
        <>
          <h4 style={{ fontSize: "0.82rem", margin: "12px 0 6px", color: "#34d399" }}>
            Community Partner Alignment
          </h4>
          {(partners.matched_partners || []).slice(0, 4).map((item) => (
            <div key={item.slug || item.entity_id} className="mini-card">
              <span className="entity-badge entity-badge--community">partner</span>{" "}
              <strong>{item.display_name || item.slug}</strong>
              <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: 4 }}>
                {item.capability} · {item.partnership_status?.replace(/_/g, " ")}
              </div>
            </div>
          ))}
          {(partners.high_priority_outreach || []).length > 0 && (
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 6 }}>
              {partners.high_priority_outreach.length} high-priority outreach target(s) in registry
            </div>
          )}
        </>
      )}

      {contributionId && reviewerId && currentEntityId && currentEntityId !== reviewerId && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
          <button type="button" className="btn btn--primary btn--sm" onClick={() => runAction("approve")}>
            Approve
          </button>
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => runAction("request-changes")}>
            Request Changes
          </button>
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => runAction("reject")}>
            Reject
          </button>
        </div>
      )}

      {message && (
        <div className={`alert${message.includes("failed") || message.includes("Error") ? " alert--error" : " alert--success"}`} style={{ marginTop: 8 }}>
          {message}
        </div>
      )}
    </div>
  );
}
