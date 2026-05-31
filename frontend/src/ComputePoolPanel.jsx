import { useCallback, useEffect, useMemo, useState } from "react";

function walletCredits(me) {
  if (!me) return null;
  return me.ai_credits ?? me.wallet?.ai_credits ?? null;
}

export default function ComputePoolPanel({ fetchJson, me, entities }) {
  const orgs = useMemo(
    () => (entities || []).filter((e) => e.entity_type === "organization"),
    [entities]
  );
  const defaultOrgId = useMemo(() => {
    const commons = orgs.find((o) => o.name === "PoCP AI Commons");
    return commons?.id || orgs[0]?.id || "";
  }, [orgs]);

  const [orgId, setOrgId] = useState(defaultOrgId);
  const [summary, setSummary] = useState(null);
  const [amount, setAmount] = useState("50");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    if (defaultOrgId && !orgId) setOrgId(defaultOrgId);
  }, [defaultOrgId, orgId]);

  const load = useCallback(async () => {
    if (!fetchJson || !orgId || !me) {
      setSummary(null);
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const data = await fetchJson(`/api/v1/compute/pools/${orgId}`);
      setSummary(data);
    } catch (err) {
      setSummary(null);
      setMessage(err.message || "Failed to load pool");
    } finally {
      setLoading(false);
    }
  }, [fetchJson, orgId, me]);

  useEffect(() => {
    load();
  }, [load]);

  const deposit = async (e) => {
    e.preventDefault();
    const value = parseFloat(amount);
    if (!value || value <= 0) {
      setMessage("Enter a positive deposit amount");
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const result = await fetchJson(`/api/v1/compute/pools/${orgId}/deposit`, {
        method: "POST",
        body: JSON.stringify({ amount: value, reason: "sponsor_deposit_ui" }),
      });
      setSummary(result);
      setMessage(`Deposited ${value} AIC into org compute pool`);
    } catch (err) {
      setMessage(err.message || "Deposit failed");
    } finally {
      setLoading(false);
    }
  };

  if (!me) {
    return (
      <section className="panel" style={{ marginTop: 16 }}>
        <h2 className="panel__title section-heading--ai">Org 算力池</h2>
        <p className="empty-state">Dev Login 后可为组织充值算力池。</p>
      </section>
    );
  }

  const credits = walletCredits(me);

  return (
    <section className="panel" style={{ marginTop: 16 }}>
      <h2 className="panel__title section-heading--ai">Org 算力池</h2>
      <p className="panel__subtitle">
        组织级算力储备 · 赞助方注入 AIC · 供 precompute / 赤字突发使用
      </p>

      <div className="profile-card profile-card--wallet" style={{ marginBottom: 16 }}>
        <div className="profile-card__balance">
          你的钱包:{" "}
          <span className="ai-credits">
            <strong>{credits ?? "—"}</strong>
          </span>{" "}
          AIC
        </div>
      </div>

      {orgs.length === 0 ? (
        <p className="empty-state">No organization entities in this instance.</p>
      ) : (
        <>
          <label className="form-row">
            <span>Organization</span>
            <select
              value={orgId}
              onChange={(e) => setOrgId(e.target.value)}
              style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border, #e2e8f0)" }}
            >
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
          </label>

          {loading && !summary && <p className="empty-state">Loading pool…</p>}

          {summary && (
            <div className="mini-card" style={{ marginBottom: 16 }}>
              <div>
                池余额: <strong>{summary.balance_credits ?? 0}</strong> AIC
              </div>
              <div className="entity-row__mission" style={{ marginTop: 6 }}>
                累计注入 {summary.total_deposited ?? 0} · 累计消耗 {summary.total_spent ?? 0}
                {summary.precompute_runs != null ? ` · precompute ${summary.precompute_runs}` : ""}
              </div>
              {summary.deficit_burst_limit != null && (
                <div className="entity-row__mission" style={{ marginTop: 4 }}>
                  赤字突发上限: {summary.deficit_burst_limit} AIC
                </div>
              )}
            </div>
          )}

          <form onSubmit={deposit}>
            <label className="form-row">
              <span>Deposit amount (AIC)</span>
              <input
                type="number"
                min="1"
                step="1"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
            </label>
            <button type="submit" className="btn btn--primary" disabled={loading || !orgId}>
              充值算力池
            </button>
          </form>
        </>
      )}

      {message && <p className="alert alert--info" style={{ marginTop: 12 }}>{message}</p>}
    </section>
  );
}
