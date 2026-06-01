import { useEffect, useState } from "react";

export default function FederationTrustPanel({ fetchJson, federationImports }) {
  const [bundle, setBundle] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!fetchJson) return;
    let cancelled = false;
    setLoading(true);
    fetchJson("/api/v1/federation/trust-policy-bundle")
      .then((data) => {
        if (!cancelled) setBundle(data);
      })
      .catch(() => {
        if (!cancelled) setBundle(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [fetchJson]);

  const importsWithValidation = [
    ...(federationImports?.received_imports || []),
    ...(federationImports?.exported_imports || []),
  ].filter((item) => item.trust_policy_valid != null || item.trust_policy_failed_count != null);

  if (loading && !bundle) {
    return (
      <div className="mini-card" style={{ marginBottom: 12 }}>
        <strong>Trust Policy Bundle</strong>
        <p className="proof-layers__meta" style={{ marginTop: 6 }}>
          Loading…
        </p>
      </div>
    );
  }

  if (!bundle) return null;

  const rules = bundle.import_rules || {};
  const trust = bundle.federation_trust || {};

  return (
    <div className="conn-panel conn-panel--trust" style={{ marginBottom: 12 }}>
      <div className="conn-panel__header">
        <div>
          <strong>Trust Policy Bundle</strong>
          <div className="conn-panel__hint">
            {bundle.bundle_id} · fingerprint {bundle.bundle_fingerprint}
          </div>
        </div>
        <span className={`conn-trust-badge${trust.trusted_node_count > 0 ? "" : " conn-trust-badge--warn"}`}>
          {trust.trusted_node_count ?? 0} trusted node(s)
        </span>
      </div>

      <div className="conn-trust-rules">
        <div className="conn-stat-row">
          <span>Import status</span>
          <span>{(rules.allowed_contribution_statuses || ["approved"]).join(", ")}</span>
        </div>
        <div className="conn-stat-row">
          <span>Invocation matrix</span>
          <span>{rules.validate_invocation_edges ? "validate" : "skip"}</span>
        </div>
        <div className="conn-stat-row">
          <span>Strict edges</span>
          <span>{rules.enforce_invocation_matrix_strict ? "block import" : "advisory"}</span>
        </div>
        <div className="conn-stat-row">
          <span>Strict mode</span>
          <span className={bundle.strict_mode_active ? "conn-trust-badge" : ""}>
            {bundle.strict_mode_active ? "POCP_STRICT_TRUST_POLICY=ON" : "advisory (env off)"}
          </span>
        </div>
        <div className="conn-stat-row">
          <span>Finalization</span>
          <span>{bundle.finalization_policy?.policy_id || "—"}</span>
        </div>
      </div>

      {importsWithValidation.length > 0 && (
        <>
          <div className="conn-label" style={{ marginTop: 12 }}>
            Import trust checks
          </div>
          {importsWithValidation.slice(0, 5).map((item) => (
            <div key={item.id} className="mini-card conn-participation">
              <strong>{item.task_title}</strong>
              <span
                className={
                  item.trust_policy_valid === false ? "conn-trust-badge conn-trust-badge--warn" : "conn-trust-badge"
                }
                style={{ marginLeft: 8 }}
              >
                {item.trust_policy_valid === false
                  ? `${item.trust_policy_failed_count ?? "?"} check(s) failed`
                  : "policy OK"}
              </span>
              <div className="conn-muted" style={{ marginTop: 4 }}>
                {item.source_node_id} · rep +{item.reputation_applied}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
