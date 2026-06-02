import { useCallback, useEffect, useState } from "react";
import FederationPeerMirrorPanel from "./FederationPeerMirrorPanel";

function shortId(id) {
  if (!id) return "—";
  return id.length > 14 ? `${id.slice(0, 10)}…` : id;
}

export default function FederationTrustPanel({ fetchJson, federationImports }) {
  const [bundle, setBundle] = useState(null);
  const [overlay, setOverlay] = useState(null);
  const [loading, setLoading] = useState(true);
  const [relayNode, setRelayNode] = useState("");
  const [relayContributionId, setRelayContributionId] = useState("");
  const [relayAutoImport, setRelayAutoImport] = useState(false);
  const [relayMessage, setRelayMessage] = useState(null);
  const [relayLoading, setRelayLoading] = useState(false);

  const loadOverlay = useCallback(() => {
    if (!fetchJson) return Promise.resolve();
    return fetchJson("/api/v1/federation/overlay/status")
      .then(setOverlay)
      .catch(() => setOverlay(null));
  }, [fetchJson]);

  useEffect(() => {
    if (!fetchJson) return;
    let cancelled = false;
    setLoading(true);
    Promise.all([
      fetchJson("/api/v1/federation/trust-policy-bundle"),
      loadOverlay(),
    ])
      .then(([bundleData]) => {
        if (!cancelled) {
          setBundle(bundleData);
          const nodes = bundleData?.federation_trust?.trusted_nodes || [];
          if (nodes.length) {
            setRelayNode((prev) => prev || nodes[0].node_id);
          }
        }
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
  }, [fetchJson, loadOverlay]);

  async function runRelay() {
    if (!fetchJson || !relayNode || !relayContributionId.trim()) {
      setRelayMessage("Select trusted node and contribution id.");
      return;
    }
    setRelayLoading(true);
    setRelayMessage(null);
    try {
      const res = await fetchJson("/api/v1/federation/overlay/relay", {
        method: "POST",
        body: JSON.stringify({
          source_node_id: relayNode,
          contribution_id: relayContributionId.trim(),
          auto_import: relayAutoImport,
        }),
      });
      const ok = res.validation?.blocking_valid;
      setRelayMessage(
        ok
          ? `Relay OK · overlay ${shortId(res.overlay_event?.event_id)}`
          : `Relay rejected · trust policy failed`
      );
      await loadOverlay();
    } catch (e) {
      setRelayMessage(String(e.message || e));
    } finally {
      setRelayLoading(false);
    }
  }

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
  const trustedNodes = trust.trusted_nodes || [];
  const fed = overlay?.federation || {};
  const recentFed = fed.recent_federation_events || [];

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

      <div className="conn-label" style={{ marginTop: 12 }}>
        Protocol overlay (L1.5)
      </div>
      <p className="conn-muted" style={{ fontSize: "0.75rem", margin: "4px 0 8px" }}>
        Mempool {overlay?.mempool_size ?? "…"} · federation offers pending{" "}
        {fed.pending_federation_offers ?? 0}
        {overlay?.last_batch?.batch_id && (
          <> · last batch {shortId(overlay.last_batch.batch_id)}</>
        )}
      </p>
      {recentFed.length > 0 ? (
        <div style={{ marginBottom: 8 }}>
          {recentFed.map((ev) => (
            <div key={ev.event_id} className="mini-card conn-participation" style={{ marginBottom: 4 }}>
              <strong>FederatedProofOffered</strong>
              <span className="conn-trust-badge" style={{ marginLeft: 8 }}>
                {ev.payload?.source_node_id || ev.node_id || "peer"}
              </span>
              <div className="conn-muted" style={{ marginTop: 4 }}>
                {ev.payload?.contribution_id || "—"} · {shortId(ev.event_id)}
                {ev.payload?.trust_policy_valid === false ? " · policy fail" : ""}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="conn-muted" style={{ fontSize: "0.75rem", marginBottom: 8 }}>
          No federation overlay events yet — use relay or federation_offer dialogue.
        </p>
      )}

      <FederationPeerMirrorPanel fetchJson={fetchJson} trustedNodes={trustedNodes} />

      {trustedNodes.length > 0 && (
        <>
          <div className="conn-label">Overlay relay (trusted peer)</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 6 }}>
            <select
              value={relayNode}
              onChange={(e) => setRelayNode(e.target.value)}
              style={{ fontSize: "0.8rem", minWidth: 140 }}
            >
              {trustedNodes.map((n) => (
                <option key={n.node_id} value={n.node_id}>
                  {n.node_id}
                </option>
              ))}
            </select>
            <input
              type="text"
              placeholder="contribution_id"
              value={relayContributionId}
              onChange={(e) => setRelayContributionId(e.target.value)}
              style={{ fontSize: "0.8rem", flex: 1, minWidth: 120 }}
            />
          </div>
          <label style={{ fontSize: "0.75rem", display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
            <input
              type="checkbox"
              checked={relayAutoImport}
              onChange={(e) => setRelayAutoImport(e.target.checked)}
            />
            Auto-import after validation
          </label>
          <button type="button" className="btn btn--small" disabled={relayLoading} onClick={runRelay}>
            Relay proof
          </button>
          {relayMessage && (
            <p style={{ fontSize: "0.75rem", marginTop: 6, color: "var(--btc)" }}>{relayMessage}</p>
          )}
        </>
      )}

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
