import { useCallback, useEffect, useMemo, useState } from "react";

import ComputeAttributionPanel from "./ComputeAttributionPanel";
import ContributionInsights from "./ContributionInsights";

function truncateHash(value, len = 14) {
  if (!value || typeof value !== "string") return "—";
  return value.length <= len ? value : `${value.slice(0, len)}…`;
}

function ProofSettlementLayers({ proof }) {
  const mcp = proof?.mcp_invocation_context;
  const training = proof?.evidence?.raw?.training;
  const ctype = proof?.contribution_event?.contribution_type;

  const hasMcp = (mcp?.trace_count || 0) > 0;
  const hasTraining = ctype === "training" && training;

  if (!hasMcp && !hasTraining) return null;

  return (
    <div className="proof-layers">
      <h4 className="proof-layers__title">Settlement layers</h4>
      {hasMcp && (
        <div className="mini-card proof-layers__card">
          <strong>MCP tool invocations</strong>
          <div className="proof-layers__meta">
            {mcp.trace_count} trace(s) · {mcp.tool_step_count} step(s)
            {(mcp.invoke_modes || []).length > 0 && (
              <span> · modes: {mcp.invoke_modes.join(", ")}</span>
            )}
          </div>
          {(mcp.capability_receipt_hashes || []).length > 0 && (
            <div className="proof-layers__meta">
              Receipt hashes: {mcp.capability_receipt_hashes.length} · verified{" "}
              {mcp.verified_receipt_count ?? 0}
            </div>
          )}
        </div>
      )}
      {hasTraining && (
        <div className="mini-card proof-layers__card">
          <strong>Training attestation</strong>
          <div className="proof-layers__meta">
            Job: {training.job_id} · {training.objective}
          </div>
          <div className="proof-layers__meta">
            Dataset: {training.dataset_ref} · Model: {training.model_ref}
          </div>
          {training.metrics?.loss_final != null && (
            <div className="proof-layers__meta">Loss: {training.metrics.loss_final}</div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ProofVerifyPanel({
  apiBase,
  contributionId,
  compact = false,
  fetchJson: fetchJsonProp,
  onSelectEntity,
  entityMap,
}) {
  const [proof, setProof] = useState(null);
  const [computeJobs, setComputeJobs] = useState(null);
  const [verifyResult, setVerifyResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchJson = useMemo(() => {
    if (fetchJsonProp) return fetchJsonProp;
    return async (path, options = {}) => {
      const res = await fetch(`${apiBase}${path}`, {
        ...options,
        headers: {
          ...(options.body ? { "Content-Type": "application/json" } : {}),
          ...(options.headers || {}),
        },
      });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      return res.json();
    };
  }, [apiBase, fetchJsonProp]);

  const fetchProof = useCallback(async () => {
    if (!contributionId) return;
    setLoading(true);
    setError(null);
    try {
      const [proofRes, jobsRes] = await Promise.all([
        fetch(`${apiBase}/api/v1/contributions/${contributionId}/proof`),
        fetch(`${apiBase}/api/v1/contributions/${contributionId}/compute-jobs`).catch(() => null),
      ]);
      if (!proofRes.ok) throw new Error(await proofRes.text());
      const data = await proofRes.json();
      setProof(data);
      if (jobsRes?.ok) {
        setComputeJobs(await jobsRes.json());
      } else {
        setComputeJobs(null);
      }
      return data;
    } catch (err) {
      setError(err.message || String(err));
      return null;
    } finally {
      setLoading(false);
    }
  }, [apiBase, contributionId]);

  useEffect(() => {
    if (contributionId) {
      fetchProof();
    }
  }, [contributionId, fetchProof]);

  const runVerify = useCallback(
    async (packet) => {
      const body = packet || proof;
      if (!body) return;
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${apiBase}/api/v1/proof/verify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ proof: body }),
        });
        if (!res.ok) throw new Error(await res.text());
        setVerifyResult(await res.json());
      } catch (err) {
        setError(err.message || String(err));
      } finally {
        setLoading(false);
      }
    },
    [apiBase, proof]
  );

  const handleExport = async () => {
    const data = proof || (await fetchProof());
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `pocp-proof-${contributionId.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleVerify = async () => {
    const data = proof || (await fetchProof());
    if (data) await runVerify(data);
  };

  if (!contributionId) return null;

  return (
    <div className={compact ? "proof-audit proof-audit--compact" : "proof-audit panel"}>
      {!compact && <h3 className="panel__title">Portable Proof — Verify, Don&apos;t Trust</h3>}
      <p className="panel__hint">
        Export a contribution proof and independently verify its hash chain — like auditing a Bitcoin full node.
      </p>
      <div className="proof-audit__actions">
        <button type="button" className="btn btn--ghost btn--sm" onClick={() => fetchProof()} disabled={loading}>
          Refresh
        </button>
        <button type="button" className="btn btn--ghost btn--sm" onClick={handleExport} disabled={loading}>
          Export proof JSON
        </button>
        <button type="button" className="btn btn--primary btn--sm" onClick={handleVerify} disabled={loading}>
          {loading ? "Verifying…" : "Verify proof"}
        </button>
      </div>
      {proof?.integrity?.proof_hash && (
        <p className="proof-audit__hash">
          Proof hash: <code>{truncateHash(proof.integrity.proof_hash, 20)}</code>
          {proof.integrity.ledger_tip_hash && (
            <>
              {" · "}
              Ledger tip: <code>{truncateHash(proof.integrity.ledger_tip_hash, 20)}</code>
            </>
          )}
        </p>
      )}
      <ProofSettlementLayers proof={proof} />
      <ComputeAttributionPanel
        computeAttribution={proof?.compute_attribution}
        computeJobs={computeJobs}
        entityMap={entityMap}
        onSelectEntity={onSelectEntity}
      />
      <ContributionInsights
        contributionId={contributionId}
        fetchJson={fetchJson}
        onSelectEntity={onSelectEntity}
      />
      {verifyResult && (
        <div className={`alert ${verifyResult.valid ? "alert--success" : "alert--error"}`}>
          {verifyResult.valid ? "Proof valid — hash chain and integrity checks passed." : "Proof verification failed."}
          <ul className="proof-audit__checks">
            {(verifyResult.checks || []).map((c) => (
              <li key={c.check}>
                {c.valid ? "✓" : "✗"} {c.check}
                {c.merkle_root && (
                  <span className="proof-audit__hash-inline">
                    {" "}
                    (root {truncateHash(c.merkle_root, 12)})
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      {proof?.ledger_merkle_inclusion && (
        <p className="proof-audit__hash">
          Ledger SPV: leaf #{proof.ledger_merkle_inclusion.leaf_index} of{" "}
          {proof.ledger_merkle_inclusion.tree_size} · root{" "}
          <code>{truncateHash(proof.ledger_merkle_inclusion.merkle_root, 16)}</code>
        </p>
      )}
      {proof?.graph_merkle_inclusion && (
        <p className="proof-audit__hash">
          Graph SPV: {proof.graph_merkle_inclusion.edge_count} edge(s) · root{" "}
          <code>{truncateHash(proof.graph_merkle_inclusion.merkle_root, 16)}</code>
        </p>
      )}
      {proof?.federation?.crypto_suite && (
        <p className="proof-audit__hash">
          Crypto suite: <code>{proof.federation.crypto_suite}</code>
          {proof.federation.signatures?.pqc && (
            <>
              {" · "}
              PQC ({proof.federation.signatures.pqc.implementation || proof.federation.signatures.pqc.algorithm})
            </>
          )}
        </p>
      )}
      {error && <div className="alert alert--error">{error}</div>}
    </div>
  );
}

export function CryptoReadinessBadge({ readiness, anchor }) {
  if (!readiness) return null;
  const hybrid = readiness.hybrid_signing_enabled;
  const suite = readiness.active_crypto_suite || "—";
  const hashAlg = readiness.active_hash_algorithm || readiness.hash_algorithm || "sha256";
  const pqcImpl = readiness.pqc_implementation?.liboqs_available ? "ML-DSA" : "stub";
  const cosignCount = anchor?.cosign_summary?.peer_count ?? anchor?.peer_attestations?.length ?? 0;

  return (
    <div
      className="network-bar__item network-bar__item--audit"
      title={`Suite: ${suite} · Hash: ${hashAlg} · PQC: ${pqcImpl}`}
    >
      <span className={`network-bar__dot${hybrid ? "" : " network-bar__dot--warn"}`} />
      Crypto:{" "}
      <span className={hybrid ? "network-bar__value" : "network-bar__value network-bar__value--warn"}>
        {hybrid ? "hybrid" : "classic"}
      </span>
      {anchor?.graph_merkle_root && (
        <>
          {" · "}
          Graph{" "}
          <span className="network-bar__mono">{truncateHash(anchor.graph_merkle_root, 8)}</span>
        </>
      )}
      {cosignCount > 0 && (
        <>
          {" · "}
          {cosignCount} cosign
        </>
      )}
    </div>
  );
}

export function LedgerVerifyBadge({ verify, anchor }) {
  if (!verify) return null;
  const valid = verify.valid && (anchor?.ledger_valid !== false);
  return (
    <div className="network-bar__item network-bar__item--audit" title={verify.tip_hash || ""}>
      <span className={`network-bar__dot${valid ? "" : " network-bar__dot--warn"}`} />
      Chain:{" "}
      <span className={valid ? "network-bar__value" : "network-bar__value network-bar__value--warn"}>
        {valid ? "valid" : "broken"}
      </span>
      {verify.tip_hash && (
        <>
          {" · "}
          Tip <span className="network-bar__mono">{truncateHash(verify.tip_hash, 10)}</span>
        </>
      )}
      {anchor?.hash_algorithm && anchor.hash_algorithm !== "sha256" && (
        <>
          {" · "}
          <span className="network-bar__mono">{anchor.hash_algorithm}</span>
        </>
      )}
    </div>
  );
}
