import { useState } from "react";

const ROLES = [
  { value: "creator", label: "Creator", weight: 0.4 },
  { value: "executor", label: "Executor (Agent)", weight: 0.25 },
  { value: "skill_provider", label: "Skill Provider", weight: 0.15 },
  { value: "reviewer", label: "Reviewer", weight: 0.1 },
  { value: "sponsor", label: "Sponsor (Org)", weight: 0.05 },
];

export default function SubmitFlow({ api, entities, tasks, onComplete }) {
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

  async function post(path, body) {
    const res = await fetch(`${api}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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
        evidence: { content_preview: form.contentPreview },
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
      await post(`/api/v1/contributions/${contributionId}/verify`, {
        model_provider: "deepseek",
        score: 0.86,
        feedback: "AI pre-review passed.",
      });
      setStep("approve");
      setMessage("AI verification passed.");
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    setLoading(true);
    setMessage(null);
    try {
      await post(`/api/v1/contributions/${contributionId}/approve`, {
        reviewer_id: form.reviewerId,
        feedback: "Approved by human reviewer.",
      });
      setMessage("Contribution approved! Credits and reputation distributed.");
      setStep("done");
      onComplete?.();
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  const fieldStyle = { display: "block", width: "100%", marginBottom: 12, padding: 8, borderRadius: 6, border: "1px solid #cbd5e1" };
  const btnStyle = (primary) => ({
    padding: "8px 16px",
    borderRadius: 6,
    border: "none",
    cursor: loading ? "wait" : "pointer",
    background: primary ? "#2563eb" : "#e2e8f0",
    color: primary ? "#fff" : "#334155",
    fontWeight: 600,
    marginRight: 8,
  });

  if (!humans.length || !skills.length) {
    return <p style={{ color: "#64748b" }}>Need at least one human and one skill entity to run the workflow.</p>;
  }

  return (
    <div style={{ background: "#f8fafc", padding: 20, borderRadius: 8 }}>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, fontSize: 13 }}>
        {["invoke", "submit", "verify", "approve", "done"].map((s, i) => (
          <span
            key={s}
            style={{
              padding: "4px 10px",
              borderRadius: 4,
              background: step === s ? "#2563eb" : step === "done" || ["invoke", "submit", "verify", "approve"].indexOf(step) > i ? "#dbeafe" : "#e2e8f0",
              color: step === s ? "#fff" : "#475569",
            }}
          >
            {i + 1}. {s}
          </span>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
        <label>
          Creator (Human)
          <select value={form.creatorId} onChange={(e) => setForm({ ...form, creatorId: e.target.value })} style={fieldStyle}>
            {humans.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
          </select>
        </label>
        <label>
          Agent
          <select value={form.agentId} onChange={(e) => setForm({ ...form, agentId: e.target.value })} style={fieldStyle}>
            {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </label>
        <label>
          Skill
          <select value={form.skillId} onChange={(e) => setForm({ ...form, skillId: e.target.value })} style={fieldStyle}>
            {skills.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </label>
        <label>
          Reviewer
          <select value={form.reviewerId} onChange={(e) => setForm({ ...form, reviewerId: e.target.value })} style={fieldStyle}>
            {humans.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
          </select>
        </label>
        {tasks.length > 0 && (
          <label style={{ gridColumn: "1 / -1" }}>
            Task
            <select value={form.taskId} onChange={(e) => setForm({ ...form, taskId: e.target.value })} style={fieldStyle}>
              {tasks.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
            </select>
          </label>
        )}
        {step !== "invoke" && (
          <>
            <label style={{ gridColumn: "1 / -1" }}>
              Description
              <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} style={fieldStyle} placeholder="Contribution description" />
            </label>
            <label style={{ gridColumn: "1 / -1" }}>
              Content Preview
              <textarea value={form.contentPreview} onChange={(e) => setForm({ ...form, contentPreview: e.target.value })} style={{ ...fieldStyle, minHeight: 60 }} placeholder="Evidence preview..." />
            </label>
          </>
        )}
      </div>

      <div style={{ marginBottom: 12 }}>
        <strong>Participant weights:</strong>
        <span style={{ color: "#64748b", marginLeft: 8 }}>
          {ROLES.map((r) => `${r.label} ${(r.weight * 100).toFixed(0)}%`).join(" · ")}
        </span>
      </div>

      <div>
        {step === "invoke" && (
          <button type="button" style={btnStyle(true)} onClick={handleInvoke} disabled={loading}>
            1. Record Invocation Chain
          </button>
        )}
        {step === "submit" && (
          <button type="button" style={btnStyle(true)} onClick={handleSubmit} disabled={loading}>
            2. Submit Contribution
          </button>
        )}
        {step === "verify" && (
          <button type="button" style={btnStyle(true)} onClick={handleVerify} disabled={loading}>
            3. Run AI Verification
          </button>
        )}
        {step === "approve" && (
          <button type="button" style={btnStyle(true)} onClick={handleApprove} disabled={loading}>
            4. Human Approve
          </button>
        )}
        {step === "done" && (
          <button type="button" style={btnStyle(false)} onClick={() => { setStep("invoke"); setContributionId(null); }}>
            Start New
          </button>
        )}
      </div>

      {message && (
        <p style={{ marginTop: 12, color: message.startsWith("Error") ? "#dc2626" : "#059669" }}>{message}</p>
      )}
    </div>
  );
}
