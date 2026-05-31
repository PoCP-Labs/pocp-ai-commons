import { useState } from "react";

function truncateHash(value, len = 14) {
  if (!value || typeof value !== "string") return "—";
  return value.length <= len ? value : `${value.slice(0, len)}…`;
}

function receiptSettlement(receipt) {
  const settlement = receipt?.settlement;
  if (settlement && (settlement.pocp_tokens_consumer != null || settlement.pocp_tokens_provider != null)) {
    return {
      spent: settlement.pocp_tokens_consumer,
      granted: settlement.pocp_tokens_provider,
      unit: settlement.token_unit || "pocp_token",
    };
  }
  return null;
}

function providerLabel(entityId, entityMap) {
  if (!entityId) return "—";
  const entity = entityMap?.[entityId];
  return entity ? `${entity.name} (${truncateHash(entityId, 10)})` : entityId;
}

export default function ComputeAttributionPanel({
  computeAttribution,
  computeJobs,
  entityMap,
  onSelectEntity,
  filterProviderId = null,
}) {
  const [showRaw, setShowRaw] = useState(false);

  const compute = computeAttribution;
  const hasCompute =
    (compute?.receipt_count || 0) > 0 || (computeJobs?.job_count || 0) > 0;

  if (!hasCompute) return null;

  let receipts = compute?.receipts || [];
  if (filterProviderId) {
    receipts = receipts.filter((r) => r.provider_entity_id === filterProviderId);
  }

  const providerIds = filterProviderId
    ? receipts.map((r) => r.provider_entity_id).filter(Boolean)
    : compute?.provider_entity_ids?.length
      ? compute.provider_entity_ids
      : [...new Set(receipts.map((r) => r.provider_entity_id).filter(Boolean))];

  const totalSpent = receipts.reduce((sum, r) => {
    const s = receiptSettlement(r);
    return sum + (typeof s?.spent === "number" ? s.spent : 0);
  }, 0);
  const totalGranted = receipts.reduce((sum, r) => {
    const s = receiptSettlement(r);
    return sum + (typeof s?.granted === "number" ? s.granted : 0);
  }, 0);
  const hasTokenSummary = totalSpent > 0 || totalGranted > 0;

  return (
    <div className="proof-layers">
      <h4 className="proof-layers__title">Compute attribution</h4>

      <div className="mini-card proof-layers__card">
        <div className="proof-layers__meta">
          {compute?.receipt_count ?? receipts.length} receipt(s) in proof
          {compute?.verified_count != null && (
            <span> · {compute.verified_count} verified</span>
          )}
          {(compute?.capabilities || []).length > 0 && (
            <span> · {compute.capabilities.join(", ")}</span>
          )}
          {compute?.training_attestation_count > 0 && (
            <span> · {compute.training_attestation_count} training attestation(s)</span>
          )}
        </div>

        {computeJobs?.job_count > 0 && (
          <div className="proof-layers__meta">
            Adapter jobs: {computeJobs.job_count}
            {(computeJobs.adapters || []).length > 0 && (
              <span> ({computeJobs.adapters.join(", ")})</span>
            )}
            {(computeJobs.adapter_modes || []).includes("live") && (
              <span className="inspiration-tag" style={{ marginLeft: 6 }}>
                live wire
              </span>
            )}
          </div>
        )}

        {(computeJobs?.adapter_modes || []).includes("live") && (
          <div className="proof-layers__meta">
            External gateway job — AKT/RNDR/IO settlement stays outside PoCP ledger.
          </div>
        )}

        {providerIds.length > 0 && (
          <div className="proof-layers__meta" style={{ marginTop: 6 }}>
            Provider{providerIds.length > 1 ? "s" : ""}:{" "}
            {providerIds.map((pid, idx) => (
              <span key={pid}>
                {idx > 0 && ", "}
                <strong>{providerLabel(pid, entityMap)}</strong>
                {onSelectEntity && (
                  <>
                    {" "}
                    <button
                      type="button"
                      className="btn btn--sm btn--ghost"
                      style={{ padding: "2px 6px" }}
                      onClick={() => onSelectEntity(pid)}
                    >
                      view
                    </button>
                  </>
                )}
              </span>
            ))}
          </div>
        )}

        {hasTokenSummary && (
          <div className="proof-layers__meta" style={{ marginTop: 6 }}>
            PoCP tokens — spent: <strong>{totalSpent}</strong>
            {totalGranted > 0 && (
              <>
                {" "}
                · granted: <strong>{totalGranted}</strong>
              </>
            )}
          </div>
        )}
      </div>

      {receipts.length > 0 && (
        <div className="compute-receipt-list">
          {receipts.map((receipt, idx) => {
            const hash = receipt?.integrity?.receipt_hash;
            const settlement = receiptSettlement(receipt);
            const pid = receipt.provider_entity_id;
            return (
              <div key={hash || idx} className="mini-card proof-layers__card compute-receipt-row">
                <strong>{receipt.capability || "compute"}</strong>
                {receipt.adapter && (
                  <span className="proof-layers__meta"> · {receipt.adapter}</span>
                )}
                {receipt.model && <span className="proof-layers__meta"> · {receipt.model}</span>}
                <div className="proof-layers__meta">
                  Provider: {providerLabel(pid, entityMap)}
                  {onSelectEntity && pid && (
                    <>
                      {" "}
                      <button
                        type="button"
                        className="btn btn--sm btn--ghost"
                        style={{ padding: "2px 6px" }}
                        onClick={() => onSelectEntity(pid)}
                      >
                        entity
                      </button>
                    </>
                  )}
                </div>
                {hash && (
                  <div className="proof-layers__meta" title={hash}>
                    Receipt hash: <code>{truncateHash(hash, 20)}</code>
                  </div>
                )}
                {settlement && (
                  <div className="proof-layers__meta">
                    {settlement.spent != null && (
                      <>
                        spent <strong>{settlement.spent}</strong> {settlement.unit}
                      </>
                    )}
                    {settlement.granted != null && settlement.granted > 0 && (
                      <>
                        {settlement.spent != null ? " · " : ""}
                        granted <strong>{settlement.granted}</strong> {settlement.unit}
                      </>
                    )}
                  </div>
                )}
                {receipt.job_id && (
                  <div className="proof-layers__meta">Job: {truncateHash(receipt.job_id, 16)}</div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {compute && (
        <div className="ledger-block__toggle">
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => setShowRaw((v) => !v)}
          >
            {showRaw ? "Hide compute_attribution JSON" : "Show compute_attribution JSON"}
          </button>
        </div>
      )}
      {showRaw && compute && (
        <pre className="ledger-block__body">{JSON.stringify(compute, null, 2)}</pre>
      )}
    </div>
  );
}
