import { useEffect, useState } from "react";
import WalletTxRow from "./WalletTxRow";

export default function EntityWalletActivity({
  entityId,
  fetchJson,
  onOpenContribution,
  onOpenLedger,
}) {
  const [summary, setSummary] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!fetchJson || !entityId) return;
    let cancelled = false;
    setLoading(true);
    Promise.all([
      fetchJson(`/api/v1/wallets/${entityId}/summary`).catch(() => null),
      fetchJson(`/api/v1/wallets/${entityId}/transactions?limit=8`).catch(() => ({ items: [] })),
    ])
      .then(([sum, tx]) => {
        if (cancelled) return;
        setSummary(sum);
        setTransactions(tx?.items || []);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [entityId, fetchJson]);

  if (loading) {
    return (
      <div className="profile-card profile-card--wallet">
        <p className="proof-layers__meta">Loading wallet activity…</p>
      </div>
    );
  }

  if (!summary) return null;

  const hasActivity = summary.transaction_count > 0;

  return (
    <div className="profile-card profile-card--wallet entity-wallet-activity">
      <div className="profile-card__balance">
        <strong>{summary.cp_balance}</strong> CP
      </div>
      <div className="profile-card__balance">
        <span className="ai-credits">
          <strong>{summary.ai_credits}</strong>
        </span>{" "}
        AI Credits
      </div>
      {hasActivity && (
        <div className="entity-wallet-activity__today">
          Today: +{summary.today_earned?.ai_credits ?? 0} BC
          {(summary.today_earned?.cp ?? 0) > 0 && ` · +${summary.today_earned.cp} CP`}
          {(summary.today_spent?.ai_credits ?? 0) > 0 && ` · -${summary.today_spent.ai_credits} BC spent`}
          {(summary.today_compute_earned > 0 || summary.today_compute_spent > 0) && (
            <>
              {" · "}compute
              {summary.today_compute_earned > 0 && ` +${summary.today_compute_earned}`}
              {summary.today_compute_spent > 0 && ` -${summary.today_compute_spent}`}
            </>
          )}
        </div>
      )}
      {summary.audit_valid ? (
        <div className="wallet-audit-hint">
          <span className="wallet-audit-hint--ok">Verified from {summary.transaction_count} tx(s)</span>
        </div>
      ) : (
        <div className="wallet-audit-hint">
          <span className="wallet-audit-hint--bad">Balance audit mismatch</span>
        </div>
      )}

      {transactions.length > 0 && (
        <div className="entity-wallet-activity__tx">
          <h4 className="entity-wallet-activity__heading">Recent activity</h4>
          {transactions.slice(0, 5).map((tx) => (
            <WalletTxRow
              key={tx.id}
              tx={tx}
              compact
              onOpenContribution={onOpenContribution}
              onOpenLedger={onOpenLedger}
            />
          ))}
        </div>
      )}
    </div>
  );
}
