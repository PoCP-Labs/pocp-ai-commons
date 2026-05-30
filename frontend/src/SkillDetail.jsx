import { useCallback, useEffect, useState } from "react";
import { publicGet } from "./auth";

const ENTITY_COLORS = {
  human: "#2563eb",
  agent: "#7c3aed",
  skill: "#059669",
  organization: "#d97706",
  llm: "#64748b",
};

function EntityBadge({ type }) {
  return (
    <span
      style={{
        background: ENTITY_COLORS[type] || "#64748b",
        color: "#fff",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 12,
        fontWeight: 600,
        textTransform: "uppercase",
      }}
    >
      {type}
    </span>
  );
}

function StatusBadge({ status }) {
  const colors = {
    active: { bg: "#dcfce7", fg: "#166534" },
    inactive: { bg: "#f1f5f9", fg: "#475569" },
    approved: { bg: "#dcfce7", fg: "#166534" },
    rejected: { bg: "#fef2f2", fg: "#991b1b" },
    submitted: { bg: "#fef9c3", fg: "#854d0e" },
    ai_verified: { bg: "#dbeafe", fg: "#1e40af" },
  };
  const c = colors[status] || { bg: "#f1f5f9", fg: "#475569" };
  return (
    <span
      style={{
        background: c.bg,
        color: c.fg,
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 12,
        fontWeight: 600,
        textTransform: "uppercase",
      }}
    >
      {status}
    </span>
  );
}

function ReputationBar({ score, maxScore }) {
  const pct = Math.min((score / (maxScore || 1)) * 100, 100);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div
        style={{
          flex: 1,
          height: 8,
          background: "#e2e8f0",
          borderRadius: 4,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: pct > 60 ? "#059669" : pct > 30 ? "#d97706" : "#dc2626",
            borderRadius: 4,
            transition: "width 0.3s ease",
          }}
        />
      </div>
      <span style={{ fontSize: 13, color: "#475569", fontWeight: 600 }}>
        {score.toFixed(1)}
      </span>
    </div>
  );
}

export default function SkillDetail({ skillId, onBack }) {
  const [skill, setSkill] = useState(null);
  const [entity, setEntity] = useState(null);
  const [contributions, setContributions] = useState([]);
  const [invocations, setInvocations] = useState([]);
  const [reputation, setReputation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);

    Promise.all([
      publicGet("/api/v1/entities"),
      publicGet("/api/v1/contributions"),
      publicGet("/api/v1/invocations"),
      publicGet("/api/v1/reputation"),
    ])
      .then(([entities, contributions, invocations, reputation]) => {
        const skillEntity = entities.find(
          (e) => e.id === skillId || e.entity_type === "skill"
        );
        if (!skillEntity) {
          setError("Skill not found");
          setLoading(false);
          return;
        }
        setEntity(skillEntity);

        // Find skill-specific record from entities that have metadata
        setSkill({
          id: skillEntity.id,
          name: skillEntity.name,
          description: skillEntity.description,
          version: skillEntity.metadata_?.version || "1.0.0",
          promptTemplate: skillEntity.metadata_?.prompt_template || "",
          maintainerId: skillEntity.owner_id,
        });

        // Filter contributions involving this skill entity
        const relevantContributions = contributions.filter((c) =>
          c.participants?.some((p) => p.entity_id === skillEntity.id)
        );
        setContributions(relevantContributions);

        // Filter invocations involving this skill entity
        const relevantInvocations = invocations.filter((inv) =>
          inv.steps?.some(
            (s) =>
              s.target_entity_id === skillEntity.id ||
              s.source_entity_id === skillEntity.id
          )
        );
        setInvocations(relevantInvocations);

        // Find reputation for this skill
        const rep = reputation.find((r) => r.entity_id === skillEntity.id);
        setReputation(rep || { score: 0, category: "skill" });

        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [skillId]);

  useEffect(() => {
    load();
  }, [load]);

  const entityMap = {};

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "3rem", color: "#64748b" }}>
        Loading skill details...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ textAlign: "center", padding: "3rem" }}>
        <p style={{ color: "#dc2626", marginBottom: 16 }}>{error}</p>
        <button
          onClick={onBack}
          style={{
            padding: "8px 16px",
            background: "#2563eb",
            color: "#fff",
            border: "none",
            borderRadius: 6,
            cursor: "pointer",
          }}
        >
          ← Back to Dashboard
        </button>
      </div>
    );
  }

  if (!skill) return null;

  const maxScore = 100;
  const skillUsagePct = contributions.length > 0
    ? ((invocations.length / Math.max(contributions.length, 1)) * 100).toFixed(0)
    : 0;

  return (
    <div>
      {/* Header with back button */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: "1.5rem",
        }}
      >
        <button
          onClick={onBack}
          style={{
            padding: "6px 12px",
            background: "#f1f5f9",
            border: "1px solid #e2e8f0",
            borderRadius: 6,
            cursor: "pointer",
            fontSize: 14,
            color: "#475569",
          }}
        >
          ← Back
        </button>
        <h2 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
          <EntityBadge type="skill" />
          {skill.name}
        </h2>
        <span
          style={{
            background: "#f0fdf4",
            color: "#166534",
            padding: "2px 8px",
            borderRadius: 4,
            fontSize: 12,
            fontFamily: "monospace",
          }}
        >
          v{skill.version}
        </span>
      </div>

      {/* Description */}
      <div
        style={{
          padding: 16,
          background: "#f8fafc",
          borderRadius: 8,
          marginBottom: "1.5rem",
        }}
      >
        <p style={{ margin: 0, color: "#334155", lineHeight: 1.6 }}>
          {skill.description || "No description available."}
        </p>
      </div>

      {/* Stats Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 12,
          marginBottom: "1.5rem",
        }}
      >
        <StatCard
          label="Reputation"
          value={reputation?.score?.toFixed(1) || "0.0"}
          color="#059669"
        />
        <StatCard
          label="Contributions"
          value={contributions.length}
          color="#2563eb"
        />
        <StatCard
          label="Invocations"
          value={invocations.length}
          color="#7c3aed"
        />
        <StatCard
          label="Skill Usage"
          value={`${skillUsagePct}%`}
          color="#d97706"
        />
      </div>

      {/* Reputation Score */}
      <section style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: 16, marginBottom: 8 }}>Reputation Score</h3>
        <div
          style={{
            padding: 16,
            background: "#faf5ff",
            borderRadius: 8,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: 4,
            }}
          >
            <span style={{ fontSize: 13, color: "#64748b" }}>
              {reputation?.category || "skill"}
            </span>
          </div>
          <ReputationBar
            score={reputation?.score || 0}
            maxScore={maxScore}
          />
        </div>
      </section>

      {/* Prompt Template */}
      {skill.promptTemplate && (
        <section style={{ marginBottom: "1.5rem" }}>
          <h3 style={{ fontSize: 16, marginBottom: 8 }}>Prompt Template</h3>
          <pre
            style={{
              background: "#1e293b",
              color: "#e2e8f0",
              padding: 16,
              borderRadius: 8,
              overflow: "auto",
              fontSize: 13,
              lineHeight: 1.5,
              maxHeight: 200,
            }}
          >
            {skill.promptTemplate}
          </pre>
        </section>
      )}

      {/* Recent Contributions */}
      <section style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: 16, marginBottom: 8 }}>
          Recent Contributions ({contributions.length})
        </h3>
        {contributions.length === 0 ? (
          <p style={{ color: "#94a3b8", fontStyle: "italic" }}>
            No contributions yet for this skill.
          </p>
        ) : (
          <div style={{ display: "grid", gap: 8 }}>
            {contributions.slice(0, 5).map((c) => (
              <div
                key={c.id}
                style={{
                  padding: 12,
                  background: "#f8fafc",
                  borderRadius: 8,
                  fontSize: 14,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 4,
                  }}
                >
                  <span style={{ fontWeight: 600, color: "#1e293b" }}>
                    {c.description?.slice(0, 60)}
                    {(c.description?.length || 0) > 60 ? "..." : ""}
                  </span>
                  <StatusBadge status={c.status} />
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {c.participants?.map((p) => {
                    // We don't have entityMap here fully, just show roles
                    return (
                      <span
                        key={p.id}
                        style={{
                          background: "#e2e8f0",
                          padding: "2px 6px",
                          borderRadius: 4,
                          fontSize: 11,
                          color: "#475569",
                        }}
                      >
                        {p.role}
                      </span>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Invocation History */}
      <section style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: 16, marginBottom: 8 }}>
          Invocation History ({invocations.length})
        </h3>
        {invocations.length === 0 ? (
          <p style={{ color: "#94a3b8", fontStyle: "italic" }}>
            No invocations recorded yet.
          </p>
        ) : (
          <div style={{ display: "grid", gap: 8 }}>
            {invocations.slice(0, 5).map((inv) => (
              <div
                key={inv.id}
                style={{
                  padding: 12,
                  background: "#f8fafc",
                  borderRadius: 8,
                  fontSize: 13,
                }}
              >
                <div style={{ color: "#64748b", marginBottom: 4 }}>
                  Initiator: <strong>{inv.initiator_id?.slice(0, 12)}...</strong>
                </div>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {inv.steps?.map((s, i) => (
                    <span key={s.id}>
                      {i > 0 && (
                        <span style={{ color: "#94a3b8", margin: "0 4px" }}>
                          →
                        </span>
                      )}
                      <span
                        style={{
                          background: "#dbeafe",
                          padding: "2px 6px",
                          borderRadius: 4,
                          fontSize: 11,
                          color: "#1e40af",
                        }}
                      >
                        {s.action}
                      </span>
                    </span>
                  ))}
                  {inv.model_provider && (
                    <span
                      style={{
                        background: "#f1f5f9",
                        padding: "2px 6px",
                        borderRadius: 4,
                        fontSize: 11,
                        color: "#475569",
                      }}
                    >
                      {inv.model_provider}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Metadata */}
      <section>
        <h3 style={{ fontSize: 16, marginBottom: 8 }}>Entity Metadata</h3>
        <div
          style={{
            padding: 16,
            background: "#f8fafc",
            borderRadius: 8,
            fontSize: 13,
            fontFamily: "monospace",
            color: "#475569",
            overflow: "auto",
          }}
        >
          <pre style={{ margin: 0 }}>
{JSON.stringify(
  {
    id: entity.id,
    type: entity.entity_type,
    name: entity.name,
    status: entity.status,
    version: skill.version,
    created_at: entity.created_at,
    owner_id: entity.owner_id || null,
  },
  null,
  2
)}
          </pre>
        </div>
      </section>
    </div>
  );
}

function StatCard({ label, value, color }) {
  return (
    <div
      style={{
        padding: 16,
        background: "#f8fafc",
        borderRadius: 8,
        border: `1px solid ${color}22`,
      }}
    >
      <div style={{ fontSize: 13, color: "#64748b", marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: 24, fontWeight: 700, color }}>
        {value}
      </div>
    </div>
  );
}
