import { useCallback, useEffect, useMemo, useState } from "react";

const NEXUS_ID = "pocp-agent-nexus-0";

const PILLARS = [
  { key: "learn", label: "Learn", desc: "Record test & acceptance outcomes" },
  { key: "grow", label: "Grow", desc: "Elevate after sustained success" },
  { key: "transform", label: "Transform", desc: "Apply approved playbook changes" },
  { key: "improve", label: "Improve", desc: "Refine after failures" },
];

const MISSION_KINDS = ["evolve", "learn", "grow", "transform", "improve"];
const OUTCOME_KINDS = ["test", "acceptance", "review", "metric", "human_feedback"];
const OUTCOME_RESULTS = ["pass", "fail", "partial"];

const PLAN_BUTTONS = [
  { id: "phase_a_p0", label: "Phase A P0 (6 handoffs)" },
  { id: "phase_a_full", label: "Phase A Full (11 handoffs)" },
];

function shortId(id) {
  if (!id) return "—";
  return id.length > 20 ? `${id.slice(0, 18)}…` : id;
}

function agentLabel(entityId, agents) {
  const a = (agents || []).find((x) => x.entity_id === entityId);
  return a?.name || shortId(entityId);
}

/** API may return boolean or string from env / JSON edge cases. */
function isTruthyFlag(value) {
  return value === true || value === "true" || value === 1 || value === "1";
}

function cursorAutomationReady(status) {
  if (!status || typeof status !== "object") return false;
  return (
    isTruthyFlag(status.automation_active) &&
    isTruthyFlag(status.sdk_installed) &&
    isTruthyFlag(status.api_key_configured)
  );
}

function CursorLastRunPanel({ processed }) {
  if (!processed?.length) return null;
  return (
    <div style={{ marginTop: 12 }}>
      <h4 style={{ fontSize: "0.85rem", margin: "0 0 8px", color: "var(--text)" }}>Last Cursor run</h4>
      {processed.map((item) => {
        const c = item.cursor || {};
        const ok = item.status === "completed" && c.ok;
        const summary = typeof c.summary === "string" ? c.summary : "";
        return (
          <div
            key={item.handoff_id}
            style={{
              marginBottom: 10,
              padding: 10,
              borderRadius: 8,
              border: `1px solid ${ok ? "rgba(52, 211, 153, 0.35)" : "rgba(248, 113, 113, 0.35)"}`,
              background: ok ? "rgba(52, 211, 153, 0.06)" : "rgba(248, 113, 113, 0.06)",
            }}
          >
            <div style={{ fontSize: "0.8rem", marginBottom: 6 }}>
              <strong>{ok ? "Completed" : item.status || "unknown"}</strong>
              {" · "}
              <span style={{ fontFamily: "var(--mono)" }}>{shortId(item.handoff_id)}</span>
              {c.run_id && (
                <>
                  {" · run "}
                  <span style={{ fontFamily: "var(--mono)" }}>{shortId(c.run_id)}</span>
                </>
              )}
            </div>
            {summary ? (
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  margin: 0,
                  fontSize: "0.78rem",
                  maxHeight: 220,
                  overflow: "auto",
                  color: "var(--text-muted)",
                }}
              >
                {summary}
              </pre>
            ) : (
              <p style={{ margin: 0, fontSize: "0.78rem", color: "var(--text-muted)" }}>
                {c.message || "No summary text returned."}
              </p>
            )}
            <details style={{ marginTop: 8, fontSize: "0.72rem" }}>
              <summary style={{ cursor: "pointer", color: "var(--text-dim)" }}>Raw JSON</summary>
              <pre style={{ whiteSpace: "pre-wrap", marginTop: 6, fontSize: "0.7rem" }}>
                {JSON.stringify(item, null, 2)}
              </pre>
            </details>
          </div>
        );
      })}
    </div>
  );
}

export default function AgentStudioPanel({ fetchJson, me }) {
  const [dash, setDash] = useState(null);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(null);
  const [missionTitle, setMissionTitle] = useState("");
  const [missionKind, setMissionKind] = useState("evolve");
  const [activeMissionId, setActiveMissionId] = useState("");

  const [handoffFrom, setHandoffFrom] = useState(NEXUS_ID);
  const [handoffTo, setHandoffTo] = useState("pocp-agent-forge-0");
  const [handoffScope, setHandoffScope] = useState("");

  const [outcomeAgent, setOutcomeAgent] = useState("pocp-agent-gauge-0");
  const [outcomeKind, setOutcomeKind] = useState("test");
  const [outcomeResult, setOutcomeResult] = useState("pass");
  const [outcomeSummary, setOutcomeSummary] = useState("");
  const [nexusTick, setNexusTick] = useState(null);
  const [cursorStatus, setCursorStatus] = useState(null);
  const [cursorLoadError, setCursorLoadError] = useState(null);
  const [superLoopStatus, setSuperLoopStatus] = useState(null);
  const [superTick, setSuperTick] = useState(null);

  const agents = useMemo(() => dash?.agents || [], [dash]);
  const nexusPm = dash?.nexus_pm || nexusTick?.status || null;

  const loadCursorStatus = useCallback(async () => {
    setCursorLoadError(null);
    try {
      const status = await fetchJson("/api/v1/agent-studio/cursor/status");
      setCursorStatus(status);
      return status;
    } catch (e) {
      setCursorStatus(null);
      setCursorLoadError(String(e.message || e));
      return null;
    }
  }, [fetchJson]);

  const loadSuperLoopStatus = useCallback(async () => {
    try {
      const status = await fetchJson("/api/v1/agent-studio/nexus/super-loop/status");
      setSuperLoopStatus(status);
      return status;
    } catch {
      setSuperLoopStatus(null);
      return null;
    }
  }, [fetchJson]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [data, planList, cursor] = await Promise.all([
        fetchJson("/api/v1/agent-studio/dashboard"),
        fetchJson("/api/v1/agent-studio/mission-plans"),
        loadCursorStatus(),
        loadSuperLoopStatus(),
      ]);
      setDash(data);
      setPlans(planList);
      if (!cursor && data?.cursor_automation) {
        setCursorStatus(data.cursor_automation);
      }
      const active = (data.recent_missions || []).find((m) => m.status === "active");
      if (active) setActiveMissionId((prev) => prev || active.id);
    } catch (e) {
      setMessage(String(e.message || e));
      await loadCursorStatus();
    } finally {
      setLoading(false);
    }
  }, [fetchJson, loadCursorStatus, loadSuperLoopStatus]);

  useEffect(() => {
    load();
  }, [load]);

  async function ensureAgents() {
    try {
      await fetchJson("/api/v1/agent-studio/ensure-agents", { method: "POST" });
      setMessage("Meta Agents registered.");
      load();
    } catch (e) {
      setMessage(String(e.message || e));
    }
  }

  async function runCursorAutomation() {
    try {
      const tick = await fetchJson("/api/v1/agent-studio/cursor/run?max_handoffs=1", {
        method: "POST",
      });
      const processed = tick.processed || [];
      const summary = processed
        .map((p) => `${p.status} (${shortId(p.handoff_id)})`)
        .join(", ");
      setMessage(
        tick.ran
          ? `Cursor ran ${processed.length} handoff(s): ${summary || "done"}`
          : `Cursor idle: ${tick.reason || "not configured"}`
      );
      await loadCursorStatus();
      load();
    } catch (e) {
      setMessage(String(e.message || e));
      await loadCursorStatus();
    }
  }

  async function runNexusSuperTick(maxCursor = 2) {
    try {
      const q = new URLSearchParams();
      if (me?.entity?.id) q.set("sponsor_entity_id", me.entity.id);
      q.set("max_cursor_handoffs", String(maxCursor));
      const tick = await fetchJson(`/api/v1/agent-studio/nexus/super-tick?${q.toString()}`, {
        method: "POST",
      });
      setSuperTick(tick);
      if (tick.nexus?.mission_id) setActiveMissionId(tick.nexus.mission_id);
      const hr = tick.human_required ? " (human review suggested)" : "";
      setMessage(
        `Super-loop: ${tick.nexus?.message || "done"} · Cursor ${tick.cursor?.processed_count ?? 0} · pending ${tick.pending_for_cursor ?? 0}${hr}`
      );
      load();
    } catch (e) {
      setMessage(String(e.message || e));
    }
  }

  async function runNexusAutopilot(force = false) {
    try {
      const q = new URLSearchParams();
      if (me?.entity?.id) q.set("sponsor_entity_id", me.entity.id);
      if (force) q.set("force_new_mission", "true");
      const tick = await fetchJson(`/api/v1/agent-studio/nexus/autopilot?${q.toString()}`, {
        method: "POST",
      });
      setNexusTick(tick);
      const qCount = tick.pending_handoff_count ?? 0;
      setMessage(`Nexus-0 PM: ${tick.message} (${qCount} open handoffs)`);
      if (tick.mission_id) setActiveMissionId(tick.mission_id);
      load();
    } catch (e) {
      setMessage(String(e.message || e));
    }
  }

  async function startMission(e) {
    e.preventDefault();
    if (!missionTitle.trim()) return;
    try {
      const m = await fetchJson("/api/v1/agent-studio/missions", {
        method: "POST",
        body: JSON.stringify({
          title: missionTitle.trim(),
          kind: missionKind,
          orchestrator_entity_id: NEXUS_ID,
          sponsor_entity_id: me?.entity?.id || null,
        }),
      });
      await fetchJson(`/api/v1/agent-studio/missions/${m.id}/activate`, { method: "POST" });
      setActiveMissionId(m.id);
      setMissionTitle("");
      setMessage(`Mission active: ${m.title}`);
      load();
    } catch (err) {
      setMessage(String(err.message || err));
    }
  }

  async function startFromPlan(planId) {
    try {
      const q = new URLSearchParams();
      if (me?.entity?.id) q.set("sponsor_entity_id", me.entity.id);
      const result = await fetchJson(
        `/api/v1/agent-studio/missions/from-plan/${planId}?${q.toString()}`,
        { method: "POST" }
      );
      setActiveMissionId(result.mission.id);
      setMessage(`Plan ${planId}: ${result.handoff_count} handoffs spawned.`);
      load();
    } catch (err) {
      setMessage(String(err.message || err));
    }
  }

  async function spawnHandoffs(planId) {
    if (!activeMissionId) {
      setMessage("Select or create an active mission first.");
      return;
    }
    try {
      const result = await fetchJson(
        `/api/v1/agent-studio/missions/${activeMissionId}/spawn-handoffs?plan_id=${planId}`,
        { method: "POST" }
      );
      setMessage(`Spawned ${result.count} handoffs (${planId}).`);
      load();
    } catch (err) {
      setMessage(String(err.message || err));
    }
  }

  async function submitHandoff(e) {
    e.preventDefault();
    try {
      await fetchJson("/api/v1/agent-studio/handoffs", {
        method: "POST",
        body: JSON.stringify({
          from_agent_entity_id: handoffFrom,
          to_agent_entity_id: handoffTo,
          mission_id: activeMissionId || null,
          scope: handoffScope.trim() || null,
        }),
      });
      setHandoffScope("");
      setMessage("Handoff recorded.");
      load();
    } catch (err) {
      setMessage(String(err.message || err));
    }
  }

  async function submitOutcome(e) {
    e.preventDefault();
    try {
      const payload = await fetchJson("/api/v1/agent-studio/outcomes", {
        method: "POST",
        body: JSON.stringify({
          agent_entity_id: outcomeAgent,
          kind: outcomeKind,
          result: outcomeResult,
          mission_id: activeMissionId || null,
          summary: outcomeSummary.trim() || null,
          auto_evaluate: true,
        }),
      });
      setOutcomeSummary("");
      setMessage(
        payload.proposal
          ? `Outcome logged; proposal: ${payload.proposal.title}`
          : "Outcome logged."
      );
      load();
    } catch (err) {
      setMessage(String(err.message || err));
    }
  }

  async function reviewProposal(proposalId, approve) {
    try {
      await fetchJson(`/api/v1/agent-studio/proposals/${proposalId}/review`, {
        method: "POST",
        body: JSON.stringify({
          approve,
          reviewer_entity_id: me?.entity?.id || NEXUS_ID,
          review_note: approve ? "Approved via Agent Studio UI" : "Rejected via Agent Studio UI",
        }),
      });
      load();
    } catch (err) {
      setMessage(String(err.message || err));
    }
  }

  async function applyProposal(proposalId) {
    try {
      const result = await fetchJson(`/api/v1/agent-studio/proposals/${proposalId}/apply`, {
        method: "POST",
        body: JSON.stringify({ actor_entity_id: me?.entity?.id || NEXUS_ID }),
      });
      const patch = result.patch_suggestion?.patch_file;
      setMessage(
        patch
          ? `Applied. Patch suggestion: ${patch} — merge into agents/prompts/ manually.`
          : "Proposal applied to agent learning profile."
      );
      load();
    } catch (err) {
      setMessage(String(err.message || err));
    }
  }

  async function completeHandoff(handoffId, status = "completed") {
    try {
      await fetchJson(`/api/v1/agent-studio/handoffs/${handoffId}/complete`, {
        method: "POST",
        body: JSON.stringify({ status, blockers: status === "blocked" ? "Blocked via UI" : null }),
      });
      setMessage(`Handoff marked ${status}.`);
      load();
    } catch (err) {
      setMessage(String(err.message || err));
    }
  }

  async function previewPatch(proposalId) {
    try {
      const data = await fetchJson(`/api/v1/agent-studio/proposals/${proposalId}/patch-preview`);
      setMessage(`Patch preview (${data.markdown?.length || 0} chars) — see API or apply to write file.`);
      console.info("[Agent Studio patch preview]\n", data.markdown);
    } catch (err) {
      setMessage(String(err.message || err));
    }
  }

  const stats = dash?.stats || {};
  const cursorAuto = cursorStatus || dash?.cursor_automation || {};
  const cursorReady = cursorAutomationReady(cursorAuto);
  const apiBase = import.meta.env.VITE_API_URL || "http://localhost:8008";
  const agentOptions = agents.length
    ? agents
    : [{ entity_id: NEXUS_ID, name: "Nexus-0" }];

  return (
    <div className="panel-stack">
      <section className="card">
        <h2 className="card__title">Agent Studio</h2>
        <p className="card__subtitle">
          Self-learning orchestration — Observe → Evaluate → Refine
        </p>
        <div className="loop-steps" style={{ marginBottom: 16 }}>
          {PILLARS.map((p) => (
            <div key={p.key} className="loop-step">
              <strong>{p.label}</strong>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{p.desc}</span>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          <button type="button" className="btn btn--ghost btn--sm" onClick={load} disabled={loading}>
            {loading ? "Loading…" : "Refresh"}
          </button>
          <button type="button" className="btn btn--sm" onClick={ensureAgents}>
            Register Meta Agents
          </button>
        </div>
        {message && <p className="form-hint">{message}</p>}
        <div className="stat-grid">
          <div className="stat-card">
            <span className="stat-card__label">Meta Agents</span>
            <span className="stat-card__value">{stats.meta_agents ?? "—"}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Active missions</span>
            <span className="stat-card__value">{stats.active_missions ?? 0}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Pending proposals</span>
            <span className="stat-card__value">{stats.pending_proposals ?? 0}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Outcomes logged</span>
            <span className="stat-card__value">{stats.outcomes_recorded ?? 0}</span>
          </div>
        </div>
      </section>

      <section className="card" style={{ borderColor: "rgba(34, 211, 238, 0.35)" }}>
        <h3 className="card__title">Cursor — Full code automation</h3>
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 12 }}>
          When configured, Agent Studio dispatches pending handoffs to the{" "}
          <strong>Cursor SDK</strong> (writes code in this repo). To <strong>see the full trial in your
          terminal</strong> (Nexus → handoff → live Cursor output), run on the host:{" "}
          <code>.\scripts\run-studio-cursor-trial.ps1</code>
        </p>
        <div style={{ fontSize: "0.8rem", marginBottom: 12, color: "var(--text-muted)" }}>
          <div style={{ marginBottom: 4, fontFamily: "var(--mono)", fontSize: "0.72rem" }}>
            API: {apiBase.replace(/^https?:\/\//, "")}
          </div>
          {cursorLoadError && (
            <div style={{ color: "var(--red)", marginBottom: 8 }}>
              Cursor status fetch failed: {cursorLoadError}
            </div>
          )}
          <div>
            Backend API: Active{" "}
            <strong>{isTruthyFlag(cursorAuto.automation_active) ? "yes" : "no"}</strong> · SDK{" "}
            <strong>{isTruthyFlag(cursorAuto.sdk_installed) ? "yes" : "no"}</strong> · API key{" "}
            <strong>{isTruthyFlag(cursorAuto.api_key_configured) ? "yes" : "no"}</strong>
            {cursorAuto.python_version && (
              <>
                {" "}
                · Python <strong>{cursorAuto.python_version}</strong>
              </>
            )}
          </div>
          <div>
            Pending handoffs: <strong>{cursorAuto.pending_for_cursor ?? 0}</strong> · Runtime:{" "}
            {cursorAuto.runtime || "local"}
          </div>
          {!cursorReady && (
            <div style={{ marginTop: 8, lineHeight: 1.5 }}>
              {cursorAuto.inactive_reason && (
                <div style={{ color: "var(--amber)", marginBottom: 6 }}>
                  {cursorAuto.inactive_reason}
                </div>
              )}
              <div>
                Edit <code>backend/.env</code> (CURSOR_API_KEY, POCP_CURSOR_AUTOMATION=true), then{" "}
                <code>docker compose build backend &amp;&amp; docker compose up -d backend</code>.
              </div>
              <div style={{ marginTop: 6 }}>
                <strong>Windows host worker</strong> (live terminal output):{" "}
                <code>.\scripts\run-studio-cursor-trial.ps1</code>
              </div>
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          <button
            type="button"
            className="btn btn--primary btn--sm"
            onClick={runCursorAutomation}
            disabled={!cursorReady || loading}
            title={
              cursorReady
                ? "Run one pending handoff via Cursor SDK in the backend container"
                : "Configure CURSOR_API_KEY and restart backend first"
            }
          >
            Run Cursor on next handoff
          </button>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={loadCursorStatus}
            disabled={loading}
          >
            Refresh Cursor status
          </button>
        </div>
        <CursorLastRunPanel processed={cursorAuto.last_tick?.processed} />
      </section>

      <section className="card" style={{ borderColor: "rgba(99, 102, 241, 0.45)" }}>
        <h3 className="card__title">Nexus Super Autopilot (PDCA)</h3>
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 12 }}>
          One tick: health probe → plan &amp; dispatch handoffs (AR) → Cursor executes Meta Agents → optional
          acceptance → learning cycle → auto repair handoffs when the platform is unhealthy. Enable background loop
          with <code>POCP_NEXUS_SUPER_LOOP=true</code> in <code>backend/.env</code> (disables the separate Cursor-only
          loop).
        </p>
        <div style={{ fontSize: "0.8rem", marginBottom: 12, color: "var(--text-muted)" }}>
          Host worker:{" "}
          <strong>{isTruthyFlag(superLoopStatus?.host_mode) ? "yes (recommended)" : "no"}</strong>
          {" · "}
          Docker loop:{" "}
          <strong>{isTruthyFlag(superLoopStatus?.backend_loop_active) ? "on" : "off"}</strong>
          {superLoopStatus?.interval_sec != null && (
            <>
              {" "}
              · interval <strong>{superLoopStatus.interval_sec}s</strong>
            </>
          )}
          {superLoopStatus?.max_cursor_per_tick != null && (
            <>
              {" "}
              · max Cursor/tick <strong>{superLoopStatus.max_cursor_per_tick}</strong>
            </>
          )}
          {(superLoopStatus?.deployment_hint || dash?.super_loop?.deployment_hint) && (
            <div style={{ marginTop: 8, lineHeight: 1.5 }}>
              {superLoopStatus?.deployment_hint || dash?.super_loop?.deployment_hint}
              {isTruthyFlag(superLoopStatus?.host_mode) && (
                <div style={{ marginTop: 6 }}>
                  Start: <code>.\scripts\run-studio-super-loop.ps1</code> · Trial:{" "}
                  <code>.\scripts\run-studio-super-loop-trial.ps1</code>
                </div>
              )}
            </div>
          )}
          {superTick?.platform_healthy != null && (
            <div style={{ marginTop: 6 }}>
              Last tick: platform{" "}
              <strong style={{ color: superTick.platform_healthy ? "var(--emerald)" : "var(--amber)" }}>
                {superTick.platform_healthy ? "healthy" : "needs repair"}
              </strong>
              {superTick.human_required_reasons?.length > 0 && (
                <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                  {superTick.human_required_reasons.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          <button
            type="button"
            className="btn btn--primary btn--sm"
            onClick={() => runNexusSuperTick(2)}
            disabled={loading}
          >
            Run super-loop tick
          </button>
          <button type="button" className="btn btn--ghost btn--sm" onClick={loadSuperLoopStatus} disabled={loading}>
            Refresh super-loop status
          </button>
        </div>
        {superTick?.cursor?.processed?.length > 0 && (
          <CursorLastRunPanel processed={superTick.cursor.processed} />
        )}
      </section>

      <section className="card" style={{ borderColor: "rgba(232, 121, 249, 0.35)" }}>
        <h3 className="card__title">Nexus-0 — Autonomous PM</h3>
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 12 }}>
          Nexus-0 decomposes <code>docs/ROADMAP-THREE-PHASES.md</code> goals, starts missions, and dispatches
          Meta Agents automatically — not only when humans type tasks. Runs on backend startup and app Refresh.
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          <button type="button" className="btn btn--primary btn--sm" onClick={() => runNexusAutopilot(false)}>
            Run Nexus autopilot
          </button>
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => runNexusAutopilot(true)}>
            Force new mission
          </button>
        </div>
        {nexusPm && (
          <div style={{ fontSize: "0.8rem", marginBottom: 12, color: "var(--text-muted)" }}>
            <div>
              Next plan: <strong>{nexusPm.next_plan_id || "continuous / idle"}</strong> · Open handoffs:{" "}
              <strong>{nexusPm.pending_handoff_count ?? 0}</strong>
            </div>
            {nexusPm.active_mission && (
              <div style={{ marginTop: 4 }}>
                Active: {nexusPm.active_mission.title} ({nexusPm.active_mission.status})
              </div>
            )}
          </div>
        )}
        {(nexusPm?.pending_dispatch || nexusTick?.dispatch_queue || []).length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <h4 style={{ fontSize: "0.8rem", marginBottom: 8 }}>Dispatch queue (agents at work)</h4>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: "0.78rem" }}>
              {(nexusPm?.pending_dispatch || nexusTick?.dispatch_queue || []).slice(0, 8).map((d) => (
                <li key={d.handoff_id} style={{ marginBottom: 6 }}>
                  <strong>{d.assignee_name}</strong>: {(d.scope || "").slice(0, 120)}
                  {(d.scope || "").length > 120 ? "…" : ""}
                </li>
              ))}
            </ul>
          </div>
        )}
        {nexusPm?.goals && (
          <details style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: 12 }}>
            <summary>Project goals ({nexusPm.goals.length})</summary>
            <ul style={{ paddingLeft: 18 }}>
              {nexusPm.goals.map((g) => (
                <li key={g.id}>
                  [{g.phase}] {g.title} → {g.owner_name || g.owner_agent_id}
                </li>
              ))}
            </ul>
          </details>
        )}
        {(nexusTick?.progress_review || nexusPm?.progress_snapshot) && (
          <details open style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: 12 }}>
            <summary>
              Progress review — {nexusTick?.completion_percent ?? nexusPm?.progress_snapshot?.completion_percent ?? 0}%
              complete
            </summary>
            <ul style={{ paddingLeft: 18, marginTop: 8 }}>
              {(nexusTick?.coaching_candidates || nexusPm?.progress_snapshot?.coaching_candidates || []).map(
                (id) => (
                  <li key={id}>
                    Coach: {agentLabel(id, agents)}
                  </li>
                )
              )}
            </ul>
            {(nexusTick?.progress_review?.agent_health || nexusPm?.progress_snapshot?.agent_health || [])
              .slice(0, 6)
              .map((a) => (
                <div key={a.entity_id} style={{ marginTop: 4 }}>
                  {a.name}: pending {a.pending_handoffs} · done {a.completed_handoffs}
                  {a.needs_coaching ? " · needs coaching" : ""}
                </div>
              ))}
          </details>
        )}
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={async () => {
            try {
              const lc = await fetchJson("/api/v1/agent-studio/nexus/learning-cycle", { method: "POST" });
              setNexusTick((prev) => ({ ...prev, ...lc }));
              setMessage("Nexus learning cycle: research + coach agents.");
              load();
            } catch (e) {
              setMessage(String(e.message || e));
            }
          }}
        >
          Run learning cycle only
        </button>
      </section>

      <section className="card">
        <h3 className="card__title">Nexus dispatch — mission plans (manual)</h3>
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 12 }}>
          Optional one-click plans if you want to override autopilot.
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          {PLAN_BUTTONS.map((p) => (
            <button key={p.id} type="button" className="btn btn--ghost btn--sm" onClick={() => startFromPlan(p.id)}>
              {p.label}
            </button>
          ))}
        </div>
        {activeMissionId && (
          <div style={{ marginBottom: 12 }}>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              Active mission: {shortId(activeMissionId)}
            </span>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
              {PLAN_BUTTONS.map((p) => (
                <button
                  key={`spawn-${p.id}`}
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => spawnHandoffs(p.id)}
                >
                  Add {p.id} handoffs
                </button>
              ))}
            </div>
          </div>
        )}
        {(plans || []).map((p) => (
          <div key={p.id} style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: 4 }}>
            {p.id}: {p.handoff_count} handoffs — {p.title}
          </div>
        ))}
      </section>

      <section className="card">
        <h3 className="card__title">Custom mission</h3>
        <form onSubmit={startMission} className="form-row">
          <input
            className="input"
            placeholder="Mission title"
            value={missionTitle}
            onChange={(e) => setMissionTitle(e.target.value)}
          />
          <select className="input" value={missionKind} onChange={(e) => setMissionKind(e.target.value)}>
            {MISSION_KINDS.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
          <button type="submit" className="btn btn--primary">
            Activate
          </button>
        </form>
      </section>

      <section className="card">
        <h3 className="card__title">Record handoff</h3>
        <form onSubmit={submitHandoff} className="form-row" style={{ flexWrap: "wrap" }}>
          <select className="input" value={handoffFrom} onChange={(e) => setHandoffFrom(e.target.value)}>
            {agentOptions.map((a) => (
              <option key={a.entity_id} value={a.entity_id}>
                {a.name || a.entity_id}
              </option>
            ))}
          </select>
          <span>→</span>
          <select className="input" value={handoffTo} onChange={(e) => setHandoffTo(e.target.value)}>
            {agentOptions.map((a) => (
              <option key={`to-${a.entity_id}`} value={a.entity_id}>
                {a.name || a.entity_id}
              </option>
            ))}
          </select>
          <input
            className="input"
            style={{ flex: "1 1 200px" }}
            placeholder="Scope / task description"
            value={handoffScope}
            onChange={(e) => setHandoffScope(e.target.value)}
          />
          <button type="submit" className="btn btn--sm">
            Log handoff
          </button>
        </form>
      </section>

      <section className="card">
        <h3 className="card__title">Record outcome (Learn)</h3>
        <form onSubmit={submitOutcome} className="form-row" style={{ flexWrap: "wrap" }}>
          <select className="input" value={outcomeAgent} onChange={(e) => setOutcomeAgent(e.target.value)}>
            {agentOptions.map((a) => (
              <option key={`o-${a.entity_id}`} value={a.entity_id}>
                {a.name || a.entity_id}
              </option>
            ))}
          </select>
          <select className="input" value={outcomeKind} onChange={(e) => setOutcomeKind(e.target.value)}>
            {OUTCOME_KINDS.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
          <select className="input" value={outcomeResult} onChange={(e) => setOutcomeResult(e.target.value)}>
            {OUTCOME_RESULTS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <input
            className="input"
            style={{ flex: "1 1 200px" }}
            placeholder="Summary (e.g. pytest green)"
            value={outcomeSummary}
            onChange={(e) => setOutcomeSummary(e.target.value)}
          />
          <button type="submit" className="btn btn--sm btn--primary">
            Log + evaluate
          </button>
        </form>
      </section>

      {(dash?.pending_proposals || []).length > 0 && (
        <section className="card">
          <h3 className="card__title">Improvement proposals</h3>
          {(dash.pending_proposals || []).map((p) => (
            <div key={p.id} className="mini-card" style={{ marginBottom: 10 }}>
              <strong>{p.title}</strong>
              <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                {agentLabel(p.agent_entity_id, agents)} · {p.kind} · {p.status}
              </div>
              {p.rationale && <p style={{ fontSize: "0.85rem" }}>{p.rationale}</p>}
              <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
                <button type="button" className="btn btn--sm btn--ghost" onClick={() => previewPatch(p.id)}>
                  Preview patch
                </button>
                <button type="button" className="btn btn--sm" onClick={() => reviewProposal(p.id, true)}>
                  Approve
                </button>
                <button type="button" className="btn btn--sm btn--ghost" onClick={() => reviewProposal(p.id, false)}>
                  Reject
                </button>
                {p.status === "approved" && (
                  <button type="button" className="btn btn--sm btn--primary" onClick={() => applyProposal(p.id)}>
                    Apply (transform)
                  </button>
                )}
              </div>
            </div>
          ))}
        </section>
      )}

      <section className="card" style={{ borderColor: "rgba(52, 211, 153, 0.35)" }}>
        <h3 className="card__title">Memory vault &amp; auto-evolution</h3>
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 12 }}>
          Each Meta Agent keeps episodic/semantic memories under{" "}
          <code>data/agent_studio/memory/</code>. Outcomes and handoffs auto-ingest; capabilities evolve after
          coaching and growth proposals.
        </p>
        {dash?.memory_vault && (
          <div style={{ fontSize: "0.8rem", marginBottom: 12, color: "var(--text-muted)" }}>
            Vault: <strong>{dash.memory_vault.total_entries ?? 0}</strong> entries · collective{" "}
            <strong>{dash.memory_vault.studio_collective_entries ?? 0}</strong>
          </div>
        )}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          <button
            type="button"
            className="btn btn--primary btn--sm"
            onClick={async () => {
              try {
                const r = await fetchJson("/api/v1/agent-studio/evolution/tick", { method: "POST" });
                setMessage(
                  `Evolution: ${r.memories_written ?? 0} memories, ${r.proposals_auto_applied ?? 0} proposals applied`
                );
                load();
              } catch (e) {
                setMessage(String(e.message || e));
              }
            }}
          >
            Run evolution tick
          </button>
        </div>
        <div className="entity-list">
          {(dash?.capability_matrix || dash?.learning_profiles || []).slice(0, 15).map((p) => (
            <div key={p.agent_entity_id} className="entity-row">
              <div>
                <strong>{agentLabel(p.agent_entity_id, agents)}</strong>
                <div className="entity-row__mission">
                  Success:{" "}
                  {p.success_rate != null ? `${Math.round(p.success_rate * 100)}%` : "—"} · Evolution v
                  {p.evolution_version ?? 0} · Memories <strong>{p.memory_count ?? 0}</strong>
                </div>
                {(p.evolved_capabilities || []).length > 0 && (
                  <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", marginTop: 4 }}>
                    Evolved: {(p.evolved_capabilities || []).slice(0, 4).join(", ")}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {(dash?.recent_handoffs || []).length > 0 && (
        <section className="card">
          <h3 className="card__title">Recent handoffs</h3>
          {(dash.recent_handoffs || []).map((h) => (
            <div key={h.id} className="mini-card" style={{ marginBottom: 8 }}>
              <div style={{ fontSize: "0.8rem" }}>
                {agentLabel(h.from_agent_entity_id, agents)} → {agentLabel(h.to_agent_entity_id, agents)} ·{" "}
                <span className={h.status === "completed" ? "network-bar__value" : ""}>{h.status}</span>
              </div>
              {h.scope && <p style={{ fontSize: "0.85rem", margin: "4px 0 0" }}>{h.scope}</p>}
              {(h.status === "pending" || h.status === "in_progress") && (
                <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
                  <button type="button" className="btn btn--sm" onClick={() => completeHandoff(h.id, "completed")}>
                    Complete
                  </button>
                  <button type="button" className="btn btn--sm btn--ghost" onClick={() => completeHandoff(h.id, "blocked")}>
                    Blocked
                  </button>
                </div>
              )}
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
