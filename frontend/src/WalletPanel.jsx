import { useCallback, useEffect, useState } from "react";
import WalletTxRow from "./WalletTxRow";
import { downloadWalletExport } from "./walletLabels";

export default function WalletPanel({
  profile,
  fetchJson,
  issuanceBudget,
  onOpenContribution,
  onOpenLedger,
  refreshKey = 0,
}) {
  const [summary, setSummary] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [txTotal, setTxTotal] = useState(0);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quote, setQuote] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [exportVerify, setExportVerify] = useState(null);

  const load = useCallback(async () => {
    if (!profile) {
      setSummary(null);
      setTransactions([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const creditType = filter === "all" ? "" : filter === "cp" ? "cp" : "ai_credits";
      const txQuery = creditType ? `?limit=30&credit_type=${creditType}` : "?limit=30";
      const [sum, tx, q] = await Promise.all([
        fetchJson("/api/v1/wallets/me/summary"),
        fetchJson(`/api/v1/wallets/me/transactions${txQuery}`),
        fetchJson("/api/v1/wallets/me/quote", { method: "POST", body: JSON.stringify({ action: "ai_chat" }) }),
      ]);
      setSummary(sum);
      setTransactions(tx.items || []);
      setTxTotal(tx.total ?? 0);
      setQuote(q);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }, [profile, fetchJson, filter, refreshKey]);

  useEffect(() => {
    load();
  }, [load]);

  const handleExport = async () => {
    setExporting(true);
    setExportVerify(null);
    try {
      const data = await fetchJson("/api/v1/wallets/me/export");
      downloadWalletExport(data, profile?.entity?.id);
      const verified = await fetchJson("/api/v1/wallets/me/export/verify", {
        method: "POST",
        body: JSON.stringify(data),
      });
      setExportVerify(verified);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setExporting(false);
    }
  };

  if (!profile) {
    return (
      <p className="empty-state">Dev Login to create a Human Entity, Wallet, and 100 starter AI Credits.</p>
    );
  }

  if (loading && !summary) {
    return <p className="empty-state">Loading wallet…</p>;
  }

  if (error && !summary) {
    return <div className="alert alert--error">{error}</div>;
  }

  const cpPolicy = summary?.rights_policy?.cp;
  const bcPolicy = summary?.rights_policy?.bc;

  return (
    <div className="wallet-panel">
      {error && <div className="alert alert--error" style={{ marginBottom: 12 }}>{error}</div>}

      <div className="wallet-panel__toolbar">
        <button type="button" className="btn btn--ghost btn--sm" onClick={handleExport} disabled={exporting}>
          {exporting ? "Exporting…" : "Export wallet JSON"}
        </button>
        <span className="wallet-panel__toolbar-hint">Offline audit · verify with POST /wallets/me/export/verify</span>
        {exportVerify && (
          <span className={exportVerify.valid ? "wallet-audit-hint--ok" : "wallet-audit-hint--bad"}>
            {exportVerify.valid ? "Export verified (transaction replay)" : "Export verify failed"}
          </span>
        )}
      </div>

      <div className="profile-grid">
        <div className="profile-card">
          <strong>{profile.entity.name}</strong>
          <div className="profile-card__email">{profile.user.email}</div>
        </div>

        <div className="profile-card profile-card--wallet">
          <div className="wallet-panel__asset">
            <span className="wallet-panel__asset-label">CP — contribution proof</span>
            <div className="profile-card__balance">
              <strong>{summary?.cp_balance ?? 0}</strong> CP
            </div>
            <span className="wallet-panel__asset-hint">
              {cpPolicy?.spendable ? "Spendable" : "Non-spendable · portable reputation proof"}
            </span>
          </div>
          <div className="wallet-panel__asset" style={{ marginTop: 12 }}>
            <span className="wallet-panel__asset-label">AI Credits — usage rights</span>
            <div className="profile-card__balance">
              <span className="ai-credits">
                <strong>{summary?.ai_credits ?? 0}</strong>
              </span>{" "}
              remaining
            </div>
            <span className="wallet-panel__asset-hint">{bcPolicy?.description || "Spend on protocol AI services"}</span>
          </div>
          {summary?.audit_valid ? (
            <div className="wallet-audit-hint">
              <span className="wallet-audit-hint--ok">Balance verified from transaction history</span>
            </div>
          ) : (
            <div className="wallet-audit-hint">
              <span className="wallet-audit-hint--bad">Balance mismatch — contact operator</span>
            </div>
          )}
        </div>
      </div>

      <div className="wallet-panel__stats">
        <div className="wallet-panel__stat">
          <span className="wallet-panel__stat-label">Today earned</span>
          <span className="wallet-panel__stat-value wallet-panel__stat-value--up">
            +{summary?.today_earned?.ai_credits ?? 0} BC
            {(summary?.today_earned?.cp ?? 0) > 0 && ` · +${summary.today_earned.cp} CP`}
          </span>
        </div>
        <div className="wallet-panel__stat">
          <span className="wallet-panel__stat-label">Today spent</span>
          <span className="wallet-panel__stat-value wallet-panel__stat-value--down">
            -{summary?.today_spent?.ai_credits ?? 0} BC
          </span>
        </div>
        {(summary?.today_compute_earned > 0 || summary?.today_compute_spent > 0) && (
          <div className="wallet-panel__stat">
            <span className="wallet-panel__stat-label">Compute settlement today</span>
            <span className="wallet-panel__stat-value">
              {summary.today_compute_earned > 0 && `+${summary.today_compute_earned} earned`}
              {summary.today_compute_earned > 0 && summary.today_compute_spent > 0 && " · "}
              {summary.today_compute_spent > 0 && `-${summary.today_compute_spent} spent`}
            </span>
          </div>
        )}
        {quote && (
          <div className="wallet-panel__stat">
            <span className="wallet-panel__stat-label">AI Chat quote</span>
            <span className="wallet-panel__stat-value">
              {quote.cost} BC → {quote.balance_after} left
              {!quote.allowed && " (insufficient)"}
            </span>
          </div>
        )}
        {issuanceBudget?.enabled && (
          <div className="wallet-panel__stat">
            <span className="wallet-panel__stat-label">Network mint left today</span>
            <span className="wallet-panel__stat-value">
              {Math.round(issuanceBudget.remaining_today?.ai_credits ?? 0)} BC
            </span>
          </div>
        )}
      </div>

      <div className="wallet-panel__filters">
        {["all", "ai_credits", "cp"].map((f) => (
          <button
            key={f}
            type="button"
            className={`btn btn--ghost wallet-panel__filter${filter === f ? " wallet-panel__filter--active" : ""}`}
            onClick={() => setFilter(f)}
          >
            {f === "all" ? "All" : f === "cp" ? "CP" : "AI Credits"}
          </button>
        ))}
        <span className="wallet-panel__tx-count">{txTotal} transaction(s)</span>
      </div>

      <div className="wallet-panel__tx-list">
        {transactions.length === 0 ? (
          <p className="empty-state">No transactions yet.</p>
        ) : (
          transactions.map((tx) => (
            <WalletTxRow
              key={tx.id}
              tx={tx}
              onOpenContribution={onOpenContribution}
              onOpenLedger={onOpenLedger}
            />
          ))
        )}
      </div>

      <div className="wallet-panel__earn-hint panel" style={{ marginTop: "1.25rem" }}>
        <h3 className="panel__title" style={{ fontSize: "0.95rem" }}>
          How to earn AI Credits
        </h3>
        <ul className="wallet-panel__earn-list">
          <li>Register as Human Entity — starter grant (typically 100 BC)</li>
          <li>Submit a contribution → auto-verify → policy finalize → BC + CP issued</li>
          <li>Agent / Skill / LLM Entities may receive BC under entity-equal policy</li>
          <li>Provide compute — settlement credits provider wallets (see compute_earn rows)</li>
        </ul>
      </div>
    </div>
  );
}
