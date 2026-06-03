import { useCallback, useEffect, useState } from "react";

function shortId(id) {
  if (!id) return "—";
  return id.length > 12 ? `${id.slice(0, 8)}…` : id;
}

export default function ProtocolDialoguePanel({
  entityId,
  entity,
  fetchJson,
  meEntityId,
  nodeId = "local",
}) {
  const meta = entity?.metadata || {};
  const roles = meta.roles || [];
  const isRemoteMirror = roles.includes("federated_mirror") || roles.includes("remote_entity");
  const homeNodeId = meta.home_node_id;
  const targetNodeId = homeNodeId || nodeId;
  const [overlay, setOverlay] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [invokeInput, setInvokeInput] = useState("Explain PoCP protocol stack in one paragraph.");
  const [execute, setExecute] = useState(false);
  const [lastResponse, setLastResponse] = useState(null);
  const [finalizeContributionId, setFinalizeContributionId] = useState("");
  const [submitTaskId, setSubmitTaskId] = useState("");
  const [attestContributionId, setAttestContributionId] = useState("");

  const loadOverlay = useCallback(() => {
    if (!fetchJson) return;
    fetchJson("/api/v1/intelligence/network/overlay/status")
      .then(setOverlay)
      .catch(() => setOverlay(null));
  }, [fetchJson]);

  useEffect(() => {
    loadOverlay();
  }, [loadOverlay]);

  async function sendDialogue(kind, extraPayload = {}, extraRefs = {}) {
    if (!fetchJson || !entityId || !meEntityId) {
      setMessage("Login required for native dialogue.");
      return;
    }
    setLoading(true);
    setMessage(null);
    const dialogueId = `dlg_ui_${Date.now().toString(36)}`;
    const envelope = {
      schema: "pocp.entity_dialogue.v0.1",
      dialogue_id: dialogueId,
      kind,
      from: { entity_id: meEntityId, node_id: nodeId },
      to: {
        entity_id: entityId,
        node_id: targetNodeId,
        ...(meta.portable_id ? { portable_id: meta.portable_id } : {}),
      },
      payload: isRemoteMirror ? { route_peer: true, ...extraPayload } : extraPayload,
      refs: extraRefs,
    };
    try {
      const res = await fetchJson(
        `/api/v1/intelligence/entities/${entityId}/dialogue`,
        {
          method: "POST",
          body: JSON.stringify(envelope),
        }
      );
      setLastResponse(res);
      setMessage(`${res.status}: ${res.result?.message || kind}`);
      loadOverlay();
    } catch (e) {
      setMessage(String(e.message || e));
    } finally {
      setLoading(false);
    }
  }

  async function runDemo() {
    if (!fetchJson) return;
    setLoading(true);
    try {
      const res = await fetchJson("/api/v1/intelligence/network/overlay/demo", {
        method: "POST",
      });
      setMessage(`Demo: ${res.peers} peers, batch ${shortId(res.batch?.batch_id)}`);
      loadOverlay();
    } catch (e) {
      setMessage(String(e.message || e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="protocol-dialogue-panel mini-card" style={{ marginBottom: 12 }}>
      <strong>Protocol dialogue (L2)</strong>
      <p style={{ fontSize: "0.75rem", color: "var(--text-dim)", margin: "6px 0 8px" }}>
        Native envelope over HTTPS — no separate physical network. Overlay mempool:{" "}
        {overlay?.mempool_size ?? "…"}
        {overlay?.pending_by_type?.FederatedProofOffered != null && (
          <> · federation {overlay.pending_by_type.FederatedProofOffered}</>
        )}
        {isRemoteMirror && (
          <> · remote mirror → {homeNodeId || "peer"} (auto peer-route)</>
        )}
      </p>
      <div className="conn-layer-tabs" style={{ marginBottom: 8 }}>
        <button
          type="button"
          className="conn-layer-tab"
          disabled={loading}
          onClick={() => sendDialogue("ping")}
        >
          Ping
        </button>
        <button
          type="button"
          className="conn-layer-tab"
          disabled={loading}
          onClick={() => sendDialogue("discover")}
        >
          Discover
        </button>
        <button
          type="button"
          className="conn-layer-tab"
          disabled={loading}
          onClick={() => sendDialogue("quote", { quote_action: "capability_invoke" })}
        >
          Quote
        </button>
        <button
          type="button"
          className="conn-layer-tab"
          disabled={loading}
          onClick={runDemo}
        >
          Overlay demo
        </button>
      </div>
      <label style={{ fontSize: "0.75rem", display: "block", marginBottom: 4 }}>
        Invoke input
        <textarea
          value={invokeInput}
          onChange={(e) => setInvokeInput(e.target.value)}
          rows={2}
          style={{ width: "100%", marginTop: 4, fontSize: "0.8rem" }}
        />
      </label>
      <label style={{ fontSize: "0.75rem", display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
        <input
          type="checkbox"
          checked={execute}
          onChange={(e) => setExecute(e.target.checked)}
        />
        Metered execute (skill/agent — consumes AI Credits)
      </label>
      <button
        type="button"
        className="btn btn--small"
        disabled={loading}
        onClick={() =>
          sendDialogue("invoke", {
            execute,
            input: invokeInput,
            llm_provider: "mock",
          })
        }
      >
        Invoke {execute ? "+ execute" : "(trace only)"}
      </button>
      <label style={{ fontSize: "0.75rem", display: "block", marginTop: 10 }}>
        Submit — task id
        <input
          type="text"
          value={submitTaskId}
          onChange={(e) => setSubmitTaskId(e.target.value)}
          placeholder="task uuid"
          style={{ width: "100%", marginTop: 4, fontSize: "0.8rem" }}
        />
      </label>
      <button
        type="button"
        className="btn btn--small"
        style={{ marginTop: 6 }}
        disabled={loading || !submitTaskId.trim()}
        onClick={() =>
          sendDialogue("submit", {
            task_id: submitTaskId.trim(),
            contribution_type: "knowledge",
            description: "Submitted via protocol dialogue UI",
            evidence: { summary: invokeInput.slice(0, 200) },
          })
        }
      >
        Submit contribution
      </button>
      <label style={{ fontSize: "0.75rem", display: "block", marginTop: 10 }}>
        Attest — contribution id
        <input
          type="text"
          value={attestContributionId}
          onChange={(e) => setAttestContributionId(e.target.value)}
          placeholder="contribution uuid"
          style={{ width: "100%", marginTop: 4, fontSize: "0.8rem" }}
        />
      </label>
      <button
        type="button"
        className="btn btn--small"
        style={{ marginTop: 6, marginRight: 8 }}
        disabled={loading || !attestContributionId.trim()}
        onClick={() =>
          sendDialogue("attest", { run_verify: true }, { contribution_id: attestContributionId.trim() })
        }
      >
        Attest (auto-verify)
      </button>
      <label style={{ fontSize: "0.75rem", display: "block", marginTop: 10 }}>
        Finalize notice — contribution id
        <input
          type="text"
          value={finalizeContributionId}
          onChange={(e) => setFinalizeContributionId(e.target.value)}
          placeholder="contribution uuid"
          style={{ width: "100%", marginTop: 4, fontSize: "0.8rem" }}
        />
      </label>
      <button
        type="button"
        className="btn btn--small"
        style={{ marginTop: 6 }}
        disabled={loading || !finalizeContributionId.trim()}
        onClick={() =>
          sendDialogue(
            "finalize_notice",
            { apply_finalize: false },
            { contribution_id: finalizeContributionId.trim() }
          )
        }
      >
        Finalize notice (verdict)
      </button>
      {message && (
        <p style={{ fontSize: "0.75rem", marginTop: 8, color: "var(--btc)" }}>{message}</p>
      )}
      {lastResponse?.result?.bindings?.length > 0 && (
        <div style={{ fontSize: "0.7rem", color: "var(--text-dim)", marginTop: 8 }}>
          <strong>Bindings</strong>
          {lastResponse.result.bindings.slice(0, 6).map((b) => (
            <div key={b.binding || b.capability_id} style={{ marginTop: 4 }}>
              {b.binding || b.capability_id}
              {b.dialogue_kind ? ` · ${b.dialogue_kind}` : ""}
            </div>
          ))}
        </div>
      )}
      {lastResponse?.result?.capabilities?.length > 0 && (
        <div style={{ fontSize: "0.7rem", color: "var(--text-dim)", marginTop: 8 }}>
          <strong>Capabilities</strong>
          {lastResponse.result.capabilities.slice(0, 6).map((c) => (
            <div key={c.capability_id || c.name} style={{ marginTop: 4 }}>
              {c.name || c.capability_id} · {c.capability_type || c.unit || "—"}
            </div>
          ))}
        </div>
      )}
      {lastResponse?.overlay?.protocol_event && (
        <p style={{ fontSize: "0.7rem", color: "var(--text-dim)", marginTop: 6 }}>
          Overlay event: {shortId(lastResponse.refs?.protocol_event_id)}
        </p>
      )}
      {lastResponse?.result?.executed && (
        <pre
          style={{
            fontSize: "0.7rem",
            marginTop: 8,
            maxHeight: 120,
            overflow: "auto",
            whiteSpace: "pre-wrap",
          }}
        >
          {(lastResponse.result.output || "").slice(0, 400)}
        </pre>
      )}
    </div>
  );
}
