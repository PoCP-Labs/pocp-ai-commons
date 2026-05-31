import { useCallback, useState } from "react";

function truncateHash(value, len = 14) {
  if (!value || typeof value !== "string") return "—";
  return value.length <= len ? value : `${value.slice(0, len)}…`;
}

export default function ProofVerifyPanel({ apiBase, contributionId, compact = false }) {
  const [proof, setProof] = useState(null);
  const [verifyResult, setVerifyResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchProof = useCallback(async () => {
    if (!contributionId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/api/v1/contributions/${contributionId}/proof`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setProof(data);
      return data;
    } catch (err) {
      setError(err.message || String(err));
      return null;
    } finally {
      setLoading(false);
    }
  }, [apiBase, contributionId]);

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
