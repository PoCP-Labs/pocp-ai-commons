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
    ])
      .then(([clarionPacket, rewardPacket, attributionProof]) => {
        if (cancelled) return;
        setClarion(clarionPacket);
        setAdvisory(rewardPacket);
        setAttribution(attributionProof);
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
              ? "Approved by human reviewer."
              : action === "reject"
                ? "Rejected by human reviewer."
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
