import { reasonLabel, transactionCategoryLabel } from "./walletLabels";

function formatTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function truncateHash(value, len = 8) {
  if (!value || typeof value !== "string") return "—";
  return value.length <= len ? value : `${value.slice(0, len)}…`;
}

export default function WalletTxRow({
  tx,
  compact = false,
  onOpenContribution,
  onOpenLedger,
}) {
  const category = tx.category;
  const ledger = tx.ledger_link;

  return (
    <div
      className={`wallet-tx${compact ? " wallet-tx--compact" : ""}${tx.amount >= 0 ? " wallet-tx--credit" : " wallet-tx--debit"}`}
    >
      <div className="wallet-tx__main">
        <span className="wallet-tx__amount">
          {tx.amount >= 0 ? "+" : ""}
          {tx.amount} {tx.credit_type === "cp" ? "CP" : "BC"}
        </span>
        <span className="wallet-tx__reason">{reasonLabel(tx.reason, category)}</span>
        {category && (
          <span className={`wallet-tx__category wallet-tx__category--${category}`}>
            {transactionCategoryLabel(category)}
          </span>
        )}
      </div>
      <div className="wallet-tx__meta">
        <span>{formatTime(tx.created_at)}</span>
        {tx.contribution_id && onOpenContribution && (
          <button
            type="button"
            className="wallet-tx__link"
            onClick={() => onOpenContribution(tx.contribution_id)}
          >
            proof · {tx.contribution_id.slice(0, 8)}…
          </button>
        )}
        {ledger && onOpenLedger && (
          <button
            type="button"
            className="wallet-tx__link wallet-tx__link--ledger"
            onClick={() => onOpenLedger(ledger)}
            title={ledger.ledger_record_hash || ledger.ledger_record_id}
          >
            ledger · {ledger.ledger_event_type?.replace(/_/g, " ")} ·{" "}
            {truncateHash(ledger.ledger_record_hash || ledger.ledger_record_id, 8)}
          </button>
        )}
        {!compact && (
          <span className="wallet-tx__balance">
            after: {tx.balance_after?.ai_credits ?? "—"} BC · {tx.balance_after?.cp_balance ?? "—"} CP
          </span>
        )}
      </div>
    </div>
  );
}
