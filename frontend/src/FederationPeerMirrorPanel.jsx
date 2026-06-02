import { useCallback, useEffect, useState } from "react";

export default function FederationPeerMirrorPanel({ fetchJson, trustedNodes = [], onMirrored }) {
  const [remoteCounts, setRemoteCounts] = useState({});
  const [mirrorBusy, setMirrorBusy] = useState(null);
  const [message, setMessage] = useState(null);
  const [registerNodeId, setRegisterNodeId] = useState("");
  const [registerBaseUrl, setRegisterBaseUrl] = useState("");

  const peers = trustedNodes.filter((n) => n.node_id && !n.is_local);

  const loadCounts = useCallback(async () => {
    if (!fetchJson || !peers.length) return;
    const next = {};
    await Promise.all(
      peers.map(async (p) => {
        const nid = p.node_id;
        try {
          const res = await fetchJson(`/api/v1/federation/peers/${encodeURIComponent(nid)}/remote-entities?limit=500`);
          next[nid] = (res.entities || []).length;
        } catch {
          next[nid] = 0;
        }
      })
    );
    setRemoteCounts(next);
  }, [fetchJson, peers]);

  useEffect(() => {
    loadCounts();
  }, [loadCounts]);

  async function mirrorNode(nodeId) {
    if (!fetchJson) return;
    setMirrorBusy(nodeId);
    setMessage(null);
    try {
      const res = await fetchJson(
        `/api/v1/federation/peers/${encodeURIComponent(nodeId)}/mirror-entities`,
        { method: "POST" }
      );
      setMessage(
        `${nodeId}: +${res.created} new, ${res.updated} updated (${res.mirrored_count} total)`
      );
      await loadCounts();
      onMirrored?.(res);
    } catch (e) {
      setMessage(String(e.message || e));
    } finally {
      setMirrorBusy(null);
    }
  }

  async function mirrorAll() {
    for (const p of peers) {
      await mirrorNode(p.node_id);
    }
  }

  async function registerPeer(e) {
    e.preventDefault();
    if (!fetchJson || !registerNodeId.trim() || !registerBaseUrl.trim()) return;
    setMirrorBusy("__register__");
    setMessage(null);
    try {
      const res = await fetchJson("/api/v1/federation/peers/register", {
        method: "POST",
        body: JSON.stringify({
          node_id: registerNodeId.trim(),
          base_url: registerBaseUrl.trim(),
          mirror_entities: true,
        }),
      });
      if (!res.in_trust_list && res.trust_config_hint) {
        setMessage(
          `Peer reachable. Add to POCP_TRUSTED_NODES then sync: ${JSON.stringify(res.trust_config_hint.example)}`
        );
      } else {
        setMessage(
          res.mirror?.mirrored_count != null
            ? `Registered · mirrored ${res.mirror.mirrored_count}`
            : "Peer probed OK"
        );
      }
      await loadCounts();
      onMirrored?.(res);
    } catch (err) {
      setMessage(String(err.message || err));
    } finally {
      setMirrorBusy(null);
    }
  }

  if (!fetchJson) return null;

  return (
    <div className="conn-trust-mirror" style={{ marginTop: 12 }}>
      <div className="conn-label">Remote entity catalog (mirror)</div>
      <p className="conn-muted" style={{ fontSize: "0.75rem", margin: "4px 0 10px" }}>
        Pull skills/agents from trusted peers into the local graph. Dialogue routes automatically via{" "}
        <code>home_node_id</code>.
      </p>

      {peers.length > 0 ? (
        <>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
            <button
              type="button"
              className="btn btn--small"
              disabled={mirrorBusy != null}
              onClick={mirrorAll}
            >
              Sync all peers
            </button>
          </div>
          {peers.map((p) => {
            const nid = p.node_id;
            const count = remoteCounts[nid];
            return (
              <div key={nid} className="mini-card conn-participation" style={{ marginBottom: 6 }}>
                <strong>{nid}</strong>
                <span className="remote-tag" style={{ marginLeft: 8 }}>
                  {count == null ? "…" : `${count} mirrored`}
                </span>
                <div className="conn-muted" style={{ marginTop: 4, fontSize: "0.72rem" }}>
                  {p.base_url || p.metadata?.base_url || "—"}
                </div>
                <button
                  type="button"
                  className="btn btn--small"
                  style={{ marginTop: 6 }}
                  disabled={mirrorBusy != null}
                  onClick={() => mirrorNode(nid)}
                >
                  {mirrorBusy === nid ? "Syncing…" : "Mirror entities"}
                </button>
              </div>
            );
          })}
        </>
      ) : (
        <p className="conn-muted" style={{ fontSize: "0.75rem", marginBottom: 8 }}>
          No trusted peers in POCP_TRUSTED_NODES — register below after configuring trust.
        </p>
      )}

      <form onSubmit={registerPeer} style={{ marginTop: 10 }}>
        <div className="conn-label">Probe &amp; register peer</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 6 }}>
          <input
            type="text"
            placeholder="node_id"
            value={registerNodeId}
            onChange={(e) => setRegisterNodeId(e.target.value)}
            style={{ fontSize: "0.8rem", minWidth: 100 }}
          />
          <input
            type="url"
            placeholder="https://peer.example.com"
            value={registerBaseUrl}
            onChange={(e) => setRegisterBaseUrl(e.target.value)}
            style={{ fontSize: "0.8rem", flex: 1, minWidth: 160 }}
          />
          <button type="submit" className="btn btn--small" disabled={mirrorBusy === "__register__"}>
            Probe
          </button>
        </div>
      </form>

      {message && (
        <p style={{ fontSize: "0.75rem", marginTop: 8, color: "var(--btc)" }}>{message}</p>
      )}
    </div>
  );
}
