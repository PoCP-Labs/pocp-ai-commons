import { useState } from "react";

const TOKEN_KEY = "pocp_token";

const ROLES = [
  { value: "creator", label: "Creator", weight: 0.4 },
  { value: "executor", label: "Executor (Agent)", weight: 0.25 },
  { value: "skill_provider", label: "Skill Provider", weight: 0.15 },
  { value: "reviewer", label: "Reviewer", weight: 0.1 },
  { value: "sponsor", label: "Sponsor (Org)", weight: 0.05 },
];

const STEPS = ["invoke", "submit", "verify", "approve", "done"];

export default function SubmitFlow({ api, entities, tasks, currentEntityId, onComplete }) {
  const humans = entities.filter((e) => e.entity_type === "human");
  const agents = entities.filter((e) => e.entity_type === "agent");
  const skills = entities.filter((e) => e.entity_type === "skill");
  const orgs = entities.filter((e) => e.entity_type === "organization");

  const [step, setStep] = useState("invoke");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const [form, setForm] = useState({
    taskId: tasks[0]?.id || "",
    creatorId: humans[0]?.id || "",
    agentId: agents[0]?.id || "",
    skillId: skills[0]?.id || "",
    reviewerId: humans[1]?.id || humans[0]?.id || "",
    sponsorId: orgs[0]?.id || "",
    description: "",
    contentPreview: "",
  });

  const [contributionId, setContributionId] = useState(null);
  const [approvalResult, setApprovalResult] = useState(null);
  const [verifyStatus, setVerifyStatus] = useState(null);

  async function post(path, body) {
    const token = localStorage.getItem(TOKEN_KEY);
    const res = await fetch(`${api}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  }

  async function handleInvoke() {
    setLoading(true);
    setMessage(null);
    try {
      await post("/api/v1/invocations", {
        initiator_id: form.creatorId,
        skill_entity_id: form.skillId,
        agent_entity_id: form.agentId,
        model_provider: "deepseek",
        task_id: form.taskId || null,
      });
      setMessage("Invocation chain recorded: Human → Agent → Skill → LLM");
      setStep("submit");
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit() {
    setLoading(true);
    setMessage(null);
    try {
      const participants = [
        { entity_id: form.creatorId, role: "creator", weight: 0.4 },
        { entity_id: form.agentId, role: "executor", weight: 0.25 },
        { entity_id: form.skillId, role: "skill_provider", weight: 0.15 },
        { entity_id: form.reviewerId, role: "reviewer", weight: 0.1 },
      ];
      if (form.sponsorId) {
        participants.push({ entity_id: form.sponsorId, role: "sponsor", weight: 0.05 });
      }

      const contrib = await post("/api/v1/contributions", {
        task_id: form.taskId,
        primary_entity_id: form.creatorId,
        contribution_type: "knowledge",
        description: form.description || "New contribution via PoCP workflow",
        evidence: {
          content_preview: form.contentPreview,
          artifact: "backend/services/proof.py",
        },
        provenance: {
          creation_mode: "ai_assisted",
          ai_tools_used: ["cursor"],
          human_experts_cited: [],
          verification_claims: [
            { claim_type: "self_reviewed", details: "Submitted via PoCP workflow UI" },
          ],
        },
        participants,
      });

      await post("/api/v1/invocations", {
        initiator_id: form.creatorId,
        skill_entity_id: form.skillId,
        agent_entity_id: form.agentId,
        model_provider: "deepseek",
        task_id: form.taskId,
        contribution_id: contrib.id,
      });

      setContributionId(contrib.id);
      setStep("verify");
      setMessage(`Contribution submitted (${contrib.id.slice(0, 8)}…)`);
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify() {
    setLoading(true);
    setMessage(null);
    try {
      await post(`/api/v1/contributions/${contributionId}/auto-verify`, {});
      setVerifyStatus("ai_verified");
      setStep("approve");
      setMessage("AI witness review completed (advisory only). Awaiting human final approval.");
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    if (!currentEntityId || currentEntityId === form.creatorId) {
      setMessage("Error: Human approval must be completed from a different reviewer account.");
      return;
    }

    setLoading(true);
    setMessage(null);
    try {
      const approved = await post(`/api/v1/contributions/${contributionId}/approve`, {
        reviewer_id: form.reviewerId,
        feedback: "Approved by human reviewer.",
      });
      setApprovalResult(approved);
      setMessage("Contribution approved! CP, Credits, and reputation recorded on ledger.");
      setStep("done");
      onComplete?.();
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  const stepIndex = STEPS.indexOf(step);

  if (!humans.length || !skills.length) {
    return <p className="empty-state">Need at least one human and one skill entity to run the workflow.</p>;
  }

  return (
    <div className="workflow-panel">
      <div className="workflow-steps">
        {STEPS.map((s, i) => (
          <span
            key={s}
            className={`workflow-step${
              step === s ? " workflow-step--active" : stepIndex > i || step === "done" ? " workflow-step--done" : ""
            }`}
          >
            {i + 1}. {s}
          </span>
        ))}
      </div>

      <div className="form-grid">
        <label className="field-label">
          Creator (Human)
          <select
            className="field-select"
            value={form.creatorId}
            onChange={(e) => setForm({ ...form, creatorId: e.target.value })}
          >
            {humans.map((h) => (
              <option key={h.id} value={h.id}>
                {h.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field-label">
          Agent
          <select
            className="field-select"
            value={form.agentId}
            onChange={(e) => setForm({ ...form, agentId: e.target.value })}
          >
            {agents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field-label">
          Skill
          <select
            className="field-select"
            value={form.skillId}
            onChange={(e) => setForm({ ...form, skillId: e.target.value })}
          >
            {skills.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field-label">
          Reviewer
          <select
            className="field-select"
            value={form.reviewerId}
            onChange={(e) => setForm({ ...form, reviewerId: e.target.value })}
          >
            {humans.map((h) => (
              <option key={h.id} value={h.id}>
                {h.name}
              </option>
            ))}
          </select>
        </label>
        {tasks.length > 0 && (
          <label className="field-label form-grid__full">
            Task
            <select
              className="field-select"
              value={form.taskId}
              onChange={(e) => setForm({ ...form, taskId: e.target.value })}
            >
              {tasks.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.title}
                </option>
              ))}
            </select>
          </label>
        )}
        {step !== "invoke" && (
          <>
            <label className="field-label form-grid__full">
              Description
              <input
                className="field-input"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Contribution description"
              />
            </label>
            <label className="field-label form-grid__full">
              Evidence Preview
              <textarea
                className="field-textarea"
                value={form.contentPreview}
                onChange={(e) => setForm({ ...form, contentPreview: e.target.value })}
                placeholder="Evidence hash material preview…"
              />
            </label>
          </>
        )}
      </div>

      <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
        <strong style={{ color: "var(--btc)" }}>Weights:</strong>{" "}
        {ROLES.map((r) => `${r.label} ${(r.weight * 100).toFixed(0)}%`).join(" · ")}
      </p>

      <div>
        {step === "invoke" && (
          <button type="button" className="btn btn--primary" onClick={handleInvoke} disabled={loading}>
            1. Record Invocation Chain
          </button>
        )}
        {step === "submit" && (
          <button type="button" className="btn btn--primary" onClick={handleSubmit} disabled={loading}>
            2. Submit Contribution
          </button>
        )}
        {step === "verify" && (
          <button type="button" className="btn btn--ai" onClick={handleVerify} disabled={loading}>
            3. AI Witness Review
          </button>
        )}
        {step === "approve" && (
          <button
            type="button"
            className="btn btn--primary"
            onClick={handleApprove}
            disabled={loading || !currentEntityId || currentEntityId === form.creatorId}
          >
            4. Human Final Approval
          </button>
        )}
        {step === "done" && (
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => {
              setStep("invoke");
              setContributionId(null);
              setApprovalResult(null);
              setVerifyStatus(null);
            }}
          >
            Start New Block
          </button>
        )}
      </div>

      {verifyStatus && step !== "invoke" && step !== "submit" && (
        <div className="alert alert--info" style={{ marginTop: 12 }}>
          AI verification status: <strong>{verifyStatus}</strong> (advisory — human approval required)
        </div>
      )}

      {approvalResult && step === "done" && (
        <div className="panel" style={{ marginTop: 12, padding: 12 }}>
          <h3 style={{ fontSize: "0.9rem", margin: "0 0 8px", color: "var(--btc)" }}>Issuance Summary</h3>
          <p style={{ margin: 0, fontSize: "0.85rem" }}>
            Status: <strong>{approvalResult.status}</strong>
          </p>
          {approvalResult.ai_verifications?.length > 0 && (
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 8 }}>
              AI witness scores recorded; human reviewer finalized this block.
            </p>
          )}
        </div>
      )}

      {message && (
        <div className={`alert${message.startsWith("Error") ? " alert--error" : " alert--success"}`} style={{ marginTop: 12 }}>
          {message}
        </div>
      )}
      {step === "approve" && (!currentEntityId || currentEntityId === form.creatorId) && (
        <div className="alert alert--info" style={{ marginTop: 12 }}>
          Human final approval requires a separate authenticated reviewer session (not the creator).
        </div>
      )}
    </div>
  );
}
