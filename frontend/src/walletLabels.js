/** Shared wallet transaction display helpers. */

export function transactionCategoryLabel(category) {
  const map = {
    registration: "Registration",
    contribution: "Contribution",
    ai_chat: "AI Chat",
    compute_earn: "Compute provider",
    compute_spend: "Compute consumer",
    federation: "Federation",
    credit: "Credit",
    debit: "Debit",
  };
  return map[category] || category || "Transaction";
}

export function reasonLabel(reason, category) {
  if (category === "compute_earn") return "Compute settlement (earned)";
  if (category === "compute_spend") return "Compute settlement (spent)";
  if (!reason) return "Transaction";
  const map = {
    "Registration grant": "Registration grant",
    "Contribution reward (creator)": "Contribution reward",
    "Contribution reward (executor)": "Contribution reward",
    "Contribution proof (creator)": "Contribution proof (CP)",
    "Contribution proof (executor)": "Contribution proof (CP)",
  };
  if (map[reason]) return map[reason];
  if (reason.toLowerCase().includes("ai chat")) return "AI Chat";
  if (reason.startsWith("compute_consumed:")) return "Compute consumed";
  if (reason.startsWith("compute_")) return "Compute provider payout";
  if (reason.startsWith("skill_orchestration:")) return "Skill orchestration payout";
  if (reason.startsWith("intel_consumed:")) return "Intelligence consumed";
  if (reason.startsWith("protocol_fee:")) return "Protocol fee";
  if (reason.toLowerCase().includes("entity-equal")) return "Entity-equal BC grant";
  return reason;
}

export function downloadWalletExport(data, entityId) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `pocp-wallet-${entityId?.slice(0, 8) || "export"}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}
