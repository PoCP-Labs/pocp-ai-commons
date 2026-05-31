import { useState } from "react";
import ProofVerifyPanel from "./ProofVerifyPanel";

const TOKEN_KEY = "pocp_token";

const ROLES = [
  { value: "creator", label: "Creator", weight: 0.4 },
  { value: "executor", label: "Executor (Agent)", weight: 0.25 },
  { value: "skill_provider", label: "Skill Provider", weight: 0.15 },
  { value: "reviewer", label: "Reviewer", weight: 0.1 },
  { value: "sponsor", label: "Sponsor (Org)", weight: 0.05 },
];

const STEPS = ["execute", "submit", "verify", "done"];

const CONTRIBUTION_TYPES = [
  { value: "knowledge", label: "Knowledge / docs" },
  { value: "training", label: "Training (Gensyn schema)" },
];

export default function SubmitFlow({ api, entities, tasks, currentEntityId, onComplete, onProofLink, onSelectEntity }) {
  const humans = entities.filter((e) => e.entity_type === "human");
  const agents = entities.filter((e) => e.entity_type === "agent");
  const skills = entities.filter((e) => e.entity_type === "skill");
  const orgs = entities.filter((e) => e.entity_type === "organization");
  const finalizers = entities.filter((e) =>
    ["agent", "llm", "skill", "human", "organization", "community"].includes(e.entity_type)
  );

  const [step, setStep] = useState("execute");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const [form, setForm] = useState({
    taskId: tasks[0]?.id || "",
    contributionType: "knowledge",
    creatorId: humans[0]?.id || "",
    agentId: agents[0]?.id || "",
    skillId: skills[0]?.id || "",
    reviewerId: finalizers.find((e) => e.id.includes("clarion"))?.id
      || agents[0]?.id
      || finalizers[0]?.id
      || "",
    sponsorId: orgs[0]?.id || "",
    description: "",
    contentPreview: "",
    executeInput: tasks[0]?.description || "Organize study notes for this task.",
    trainingJobId: "",
    trainingObjective: "fine_tune_study_agent",
    trainingDatasetRef: "dataset:pocp-demo",
    trainingModelRef: "huggingface:org/model",
    trainingLoss: "",
  });

  const [contributionId, setContributionId] = useState(null);
  const [executionTraceId, setExecutionTraceId] = useState(null);
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

  function copyProofLink() {
    if (!contributionId) return;
    const url = `${window.location.origin}${window.location.pathname}?proof=${contributionId}`;
    navigator.clipboard?.writeText(url).catch(() => {});
    setMessage("Proof link copied — share or open in Verify Proof tab.");
    onProofLink?.(contributionId);
  }

  async function handleInvoke() {
    setLoading(true);
    setMessage(null);
    try {
      if (form.contributionType === "training") {
        const jobId = form.trainingJobId || `train-${Date.now().toString(36)}`;
        setForm((f) => ({
          ...f,
          trainingJobId: jobId,
          description: f.description || `Training: ${f.trainingObjective}`,
          contentPreview: `dataset=${f.trainingDatasetRef}; model=${f.trainingModelRef}`,
        }));
        setMessage(`Training template ready — job ${jobId}`);
        setStep("submit");
        setLoading(false);
        return;
      }

      const agent = agents.find((a) => a.id === form.agentId);
      const useStudyAgent = agent?.name === "StudyAgent";

      let result;
      if (useStudyAgent) {
        result = await post("/api/v1/intelligence/agents/study/run", {
          topic: form.executeInput,
          task_id: form.taskId || null,
          agent_entity_id: form.agentId,
          skill_entity_id: form.skillId,
          llm_provider: "mock",
          submit_contribution: false,
        });
        setExecutionTraceId(result.trace_id);
        setForm((f) => ({
          ...f,
          contentPreview: (result.draft || result.output || "").slice(0, 2000),
          description: f.description || `Study notes via StudyAgent (${result.trace_id?.slice(0, 8)}…)`,
        }));
      } else if (form.agentId) {
        result = await post(`/api/v1/capabilities/agents/${form.agentId}/execute`, {
          input: form.executeInput,
          skill_entity_id: form.skillId,
          task_id: form.taskId || null,
          llm_provider: "mock",
          include_receipt: false,
        });
        setExecutionTraceId(result.trace_id);
        setForm((f) => ({
          ...f,
          contentPreview: (result.output || "").slice(0, 2000),
          description: f.description || `Output via ${agent?.name || "Agent"} + Skill`,
        }));
      } else {
        result = await post(`/api/v1/capabilities/skills/${form.skillId}/execute`, {
          input: form.executeInput,
          task_id: form.taskId || null,
          llm_provider: "mock",
        });
        setExecutionTraceId(result.trace_id);
        setForm((f) => ({
          ...f,
          contentPreview: (result.output || "").slice(0, 2000),
          description: f.description || "Output via Skill execution",
        }));
      }

      setMessage(
        `Executed ${useStudyAgent ? "StudyAgent" : agent?.name || "Skill"} — trace ${result.trace_id?.slice(0, 8)}…`
      );
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

      const isTraining = form.contributionType === "training";
      const evidence = isTraining
        ? {
            training: {
              job_id: form.trainingJobId || `train-${Date.now().toString(36)}`,
              objective: form.trainingObjective,
              dataset_ref: form.trainingDatasetRef,
              model_ref: form.trainingModelRef,
              ...(form.trainingLoss !== "" && form.trainingLoss != null
                ? { metrics: { loss_final: Number(form.trainingLoss) } }
                : {}),
            },
            content_preview: form.contentPreview,
          }
        : {
            content_preview: form.contentPreview,
            artifact: "backend/services/proof.py",
            capability_execution: {
              trace_id: executionTraceId,
              agent_entity_id: form.agentId,
              skill_entity_id: form.skillId,
            },
          };

      const contrib = await post("/api/v1/contributions", {
        task_id: form.taskId,
        primary_entity_id: form.creatorId,
        contribution_type: form.contributionType,
        description:
          form.description ||
          (isTraining ? `Training contribution: ${form.trainingObjective}` : "New contribution via PoCP workflow"),
        evidence,
        provenance: isTraining
          ? {
              creation_mode: "mixed",
              ai_tools_used: ["compute_adapter"],
              verification_claims: [
                { claim_type: "training_attestation", details: "Submitted via training workflow UI" },
              ],
            }
          : {
              creation_mode: "ai_assisted",
              ai_tools_used: ["cursor"],
              human_experts_cited: [],
              verification_claims: [
                { claim_type: "self_reviewed", details: "Submitted via PoCP workflow UI" },
              ],
            },
        participants,
      });

      if (!isTraining) {
        await post("/api/v1/invocations", {
          initiator_id: form.creatorId,
          skill_entity_id: form.skillId,
          agent_entity_id: form.agentId,
          model_provider: "deepseek",
          task_id: form.taskId,
          contribution_id: contrib.id,
        });
      } else {
        const token = localStorage.getItem(TOKEN_KEY);
        if (token) {
          try {
            const imported = await post("/api/v1/compute/adapters/gensyn/import", {
              entity_id: "pocp-adapt-gensyn-ui",
              display_name: "Gensyn Stub (UI)",
              offers: [{ capability: "training", adapters: ["gensyn"] }],
            });
            const job = await post("/api/v1/compute/adapters/gensyn/jobs", {
              capability: "training",
              provider_entity_id: imported.entity_id,
              contribution_id: contrib.id,
              task_id: form.taskId,
              constraints: {
                objective: form.trainingObjective,
                job_id: form.trainingJobId || evidence.training?.job_id,
                dataset_ref: form.trainingDatasetRef,
                model_ref: form.trainingModelRef,
              },
            });
            let polled = job;
            for (let i = 0; i < 5 && polled.status !== "completed"; i += 1) {
              polled = await post(
                `/api/v1/compute/adapters/gensyn/jobs/${job.job_id}/poll`,
                {}
              );
            }
            const attestation = polled.compute_receipt?.integrity?.training_attestation;
            setMessage(
              attestation
                ? `Training submitted + Gensyn stub attestation (${polled.status})`
                : `Training submitted; adapter job ${polled.status || job.status}`
            );
          } catch (adapterErr) {
            setMessage(
              `Contribution submitted; Gensyn adapter skipped: ${adapterErr.message}`
            );
          }
        } else {
          setMessage(
            `Contribution submitted (${contrib.id.slice(0, 8)}…). Dev login to dispatch Gensyn adapter job.`
          );
        }
      }

      if (!isTraining) {
        setMessage(`Contribution submitted (${contrib.id.slice(0, 8)}…)`);
      }

      setContributionId(contrib.id);
      setStep("verify");
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
      const result = await post(`/api/v1/contributions/${contributionId}/auto-verify`, {});
      const status = result.status || "ai_verified";
      setVerifyStatus(status);
      const fin = result.finalization;
      const verdict = result.verdict?.verdict || fin?.verdict;
      if (status === "approved" || fin?.applied) {
        setApprovalResult(result);
        setStep("done");
        setMessage(
          `Auto-finalized by Entity policy (verdict ${verdict || "PASS"}, finalizer ${fin?.finalizer_entity_id?.slice(0, 12) || "delegate"}…).`
        );
        onComplete?.();
      } else {
        setStep("verify");
        setMessage(`Verification did not pass (verdict ${verdict || "FAIL"}). Revise evidence and retry.`);
      }
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
          Finalizer Entity (participant)
          <select
            className="field-select"
            value={form.reviewerId}
            onChange={(e) => setForm({ ...form, reviewerId: e.target.value })}
          >
            {finalizers.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name} ({e.entity_type})
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
        <label className="field-label form-grid__full">
          Contribution type
          <select
            className="field-select"
            value={form.contributionType}
            onChange={(e) => setForm({ ...form, contributionType: e.target.value })}
          >
            {CONTRIBUTION_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
        {step === "execute" && form.contributionType === "training" && (
          <>
            <label className="field-label">
              Training job ID
              <input
                className="field-input"
                value={form.trainingJobId}
                onChange={(e) => setForm({ ...form, trainingJobId: e.target.value })}
                placeholder="train-001 (auto if empty)"
              />
            </label>
            <label className="field-label">
              Objective
              <input
                className="field-input"
                value={form.trainingObjective}
                onChange={(e) => setForm({ ...form, trainingObjective: e.target.value })}
              />
            </label>
            <label className="field-label form-grid__full">
              Dataset ref
              <input
                className="field-input"
                value={form.trainingDatasetRef}
                onChange={(e) => setForm({ ...form, trainingDatasetRef: e.target.value })}
                placeholder="dataset:entity-id or CID"
              />
            </label>
            <label className="field-label form-grid__full">
              Model ref
              <input
                className="field-input"
                value={form.trainingModelRef}
                onChange={(e) => setForm({ ...form, trainingModelRef: e.target.value })}
                placeholder="huggingface:org/model"
              />
            </label>
            <label className="field-label">
              Final loss (optional)
              <input
                className="field-input"
                type="number"
                step="any"
                value={form.trainingLoss}
                onChange={(e) => setForm({ ...form, trainingLoss: e.target.value })}
              />
            </label>
          </>
        )}
        {step === "execute" && form.contributionType !== "training" && (
          <label className="field-label form-grid__full">
            Execute input (Agent + Skill)
            <textarea
              className="field-textarea"
              value={form.executeInput}
              onChange={(e) => setForm({ ...form, executeInput: e.target.value })}
              placeholder="What should the Agent/Skill produce?"
            />
          </label>
        )}
        {step !== "execute" && (
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
        {step === "execute" && (
          <button type="button" className="btn btn--primary" onClick={handleInvoke} disabled={loading}>
            {form.contributionType === "training" ? "1. Prepare training submit" : "1. Execute Agent + Skill"}
          </button>
        )}
        {step === "submit" && (
          <button type="button" className="btn btn--primary" onClick={handleSubmit} disabled={loading}>
            2. Submit Contribution
          </button>
        )}
        {step === "verify" && (
          <button type="button" className="btn btn--ai" onClick={handleVerify} disabled={loading}>
            3. Witness Verify + Auto-Finalize
          </button>
        )}
        {step === "done" && (
          <>
            <button type="button" className="btn btn--ghost" onClick={copyProofLink} disabled={!contributionId}>
              Copy proof link
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => {
                setStep("execute");
                setContributionId(null);
                setExecutionTraceId(null);
                setApprovalResult(null);
                setVerifyStatus(null);
              }}
            >
              Start New Block
            </button>
          </>
        )}
      </div>

      {verifyStatus && step !== "execute" && step !== "submit" && (
        <div className="alert alert--info" style={{ marginTop: 12 }}>
          Witness status: <strong>{verifyStatus}</strong> (Entity-equal auto-finalization under policy)
        </div>
      )}

      {contributionId && (step === "verify" || step === "done") && (
        <ProofVerifyPanel
          apiBase={api}
          contributionId={contributionId}
          compact={step !== "done"}
          onSelectEntity={onSelectEntity}
          entityMap={Object.fromEntries(entities.map((e) => [e.id, e]))}
        />
      )}

      {approvalResult && step === "done" && (
        <div className="panel" style={{ marginTop: 12, padding: 12 }}>
          <h3 style={{ fontSize: "0.9rem", margin: "0 0 8px", color: "var(--btc)" }}>Issuance Summary</h3>
          <p style={{ margin: 0, fontSize: "0.85rem" }}>
            Status: <strong>{approvalResult.status}</strong>
          </p>
          {approvalResult.ai_verifications?.length > 0 && (
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 8 }}>
              AI witness scores recorded; finalizer Entity recorded in this block.
            </p>
          )}
        </div>
      )}

      {message && (
        <div className={`alert${message.startsWith("Error") ? " alert--error" : " alert--success"}`} style={{ marginTop: 12 }}>
          {message}
        </div>
      )}
    </div>
  );
}
