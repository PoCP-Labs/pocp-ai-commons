function truncateHash(value, len = 16) {
  if (!value || typeof value !== "string") return "—";
  return value.length <= len ? value : `${value.slice(0, len)}…`;
}

function CheckRow({ ok, label, detail }) {
  return (
    <div className={`crypto-panel__row${ok ? "" : " crypto-panel__row--warn"}`}>
      <span className="crypto-panel__icon">{ok ? "✓" : "○"}</span>
      <span className="crypto-panel__label">{label}</span>
      {detail && <code className="crypto-panel__detail">{detail}</code>}
    </div>
  );
}

export default function CryptoReadinessPanel({ readiness, anchor, ledgerVerify, walletAudit }) {
  if (!readiness && !anchor) return null;

  const hybrid = readiness?.hybrid_signing_enabled;
  const suite = readiness?.active_crypto_suite || "—";
  const minSuite = readiness?.minimum_accepted_crypto_suite || "—";
  const hashAlg = readiness?.active_hash_algorithm || anchor?.hash_algorithm || "sha256";
  const pqc = readiness?.pqc_implementation || {};
  const pqcLabel = pqc.liboqs_available ? `ML-DSA (${pqc.liboqs_mechanism})` : "dev stub";
  const cosign = anchor?.peer_attestations?.length ?? anchor?.cosign_summary?.peer_count ?? 0;
  const graphRoot = anchor?.graph_merkle_root;
  const ledgerRoot = anchor?.merkle_root;
  const chainOk = ledgerVerify?.valid && anchor?.ledger_valid !== false;

  return (
    <section className="panel crypto-panel">
      <h2 className="panel__title">Network Memory &amp; Quantum Readiness</h2>
      <p className="panel__subtitle">
        Verify-don&apos;t-trust — hash chain, graph Merkle, hybrid signatures (Bitcoin-inspired audit layer)
      </p>

      <div className="crypto-panel__grid">
        <div className="crypto-panel__card">
          <h3 className="crypto-panel__heading">Crypto suite</h3>
          <CheckRow ok={hybrid} label="Hybrid signing" detail={suite} />
          <CheckRow ok={readiness?.pqc_public_key_configured} label="PQC key configured" detail={pqcLabel} />
          <CheckRow
            ok={readiness?.require_pqc_signature !== true || hybrid}
            label="Min suite policy"
            detail={minSuite}
          />
          <CheckRow ok label="Hash algorithm" detail={hashAlg} />
        </div>

        <div className="crypto-panel__card">
          <h3 className="crypto-panel__heading">Public memory</h3>
          <CheckRow ok={chainOk} label="Ledger chain" detail={chainOk ? "valid" : "check failed"} />
          <CheckRow ok={Boolean(ledgerRoot)} label="Ledger Merkle root" detail={truncateHash(ledgerRoot, 12)} />
          <CheckRow ok={Boolean(graphRoot)} label="Graph Merkle root" detail={truncateHash(graphRoot, 12)} />
          <CheckRow ok={walletAudit?.valid !== false} label="Wallet replay audit" detail={walletAudit?.valid ? "ok" : "—"} />
          {cosign > 0 && <CheckRow ok label="Peer cosignatures" detail={`${cosign} peer(s)`} />}
        </div>
      </div>

      {anchor?.anchored_at && (
        <p className="crypto-panel__meta">
          Anchor: {anchor.node_id} · {anchor.anchored_at.slice(0, 19)}Z · {anchor.graph_edge_count ?? 0} graph edges
        </p>
      )}
    </section>
  );
}
