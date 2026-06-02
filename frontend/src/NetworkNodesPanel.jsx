import { useCallback, useEffect, useState } from "react";
import { fetchJsonOptional, truncateHash } from "./appShell.js";

function layoutPositions(local, peers, satellites, width, height) {
  const cx = width / 2;
  const cy = height / 2;
  const pos = new Map();

  if (local) {
    pos.set(local.id, { x: cx, y: cy, kind: "local" });
  }

  const peerRing = Math.min(110, 50 + peers.length * 14);
  peers.forEach((p, idx) => {
    const angle = (Math.PI * 2 * idx) / Math.max(1, peers.length) - Math.PI / 2;
    pos.set(p.id, {
      x: cx + Math.cos(angle) * peerRing,
      y: cy + Math.sin(angle) * peerRing,
      kind: "peer",
    });
  });

  const satRing = Math.min(165, 90 + Math.min(satellites.length, 24) * 3);
  satellites.forEach((s, idx) => {
    const anchorId = s.peer_entity_id && pos.has(s.peer_entity_id) ? s.peer_entity_id : local?.id;
    const anchor = pos.get(anchorId) || { x: cx, y: cy };
    const angle = (Math.PI * 2 * idx) / Math.max(1, satellites.length);
    pos.set(s.id, {
      x: anchor.x + Math.cos(angle) * (satRing * 0.55),
      y: anchor.y + Math.sin(angle) * (satRing * 0.55),
      kind: "mirror",
    });
  });

  return pos;
}

export default function NetworkNodesPanel({ fetchJson, onSelectEntity, onRefreshGraph }) {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [registerNodeId, setRegisterNodeId] = useState("");
  const [registerBaseUrl, setRegisterBaseUrl] = useState("");
  const [registering, setRegistering] = useState(false);
  const [discoverSeeds, setDiscoverSeeds] = useState("");
  const [discovering, setDiscovering] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const request =
        fetchJson ||
        (async (path) => {
          const value = await fetchJsonOptional(path, null);
          if (value == null) throw new Error("request failed");
          return value;
        });

      // Preferred API (new backend)
      let data = await fetchJsonOptional("/api/v1/federation/network/overview", null);

      // Backward-compatible fallback for backends without /network/overview
      if (!data || !Array.isArray(data.nodes)) {
        const legacy = await request("/api/v1/federation/peers/entities");
        const legacyNodes = Array.isArray(legacy?.entities) ? legacy.entities : [];
        const nodes = legacyNodes.map((n) => ({
          id: n.entity_id || n.id,
          entity_id: n.entity_id || n.id,
          node_id: n.metadata?.node_id || n.node_id || n.name,
          name: n.name || n.node_id || "Node",
          is_local: Boolean(n.is_local),
          kind: n.is_local ? "local" : "peer",
          base_url: n.metadata?.base_url || null,
          trust_weight: n.metadata?.trust_weight ?? null,
          mirror_count: 0,
          metadata: n.metadata || {},
        }));
        const local = nodes.find((n) => n.is_local);
        const edges =
          local == null
            ? []
            : nodes
                .filter((n) => !n.is_local)
                .map((n) => ({ source: local.id, target: n.id, relation: "federated_with" }));
        data = {
          schema: "pocp.federation_network_overview.v0.1-legacy",
          local_node_id: legacy?.local_node_id || null,
          node_count: nodes.length,
          trusted_peer_count: nodes.filter((n) => !n.is_local).length,
          mirror_count: 0,
          trust_source: "legacy",
          nodes,
          satellites: [],
          edges,
          setup_hint:
            nodes.filter((n) => !n.is_local).length > 0
              ? null
              : {
                  message: "Configure POCP_TRUSTED_NODES or backend/config/trusted_nodes.yaml",
                  example_env:
                    '[{"node_id":"peer-a","base_url":"http://localhost:8009","trust_weight":0.8}]',
                },
        };
      }

      setOverview(data);
    } catch (e) {
      setError(String(e.message || e));
      setOverview(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const registerPeer = async (e) => {
    e.preventDefault();
    if (!registerNodeId.trim() || !registerBaseUrl.trim()) return;
    setRegistering(true);
    setError(null);
    try {
      const request =
        fetchJson ||
        (async (path, options) => {
          const value = await fetchJsonOptional(path, null);
          if (value == null) throw new Error("request failed");
          return value;
        });
      await request("/api/v1/federation/peers/register", {
        method: "POST",
        body: JSON.stringify({
          node_id: registerNodeId.trim(),
          base_url: registerBaseUrl.trim(),
          mirror_entities: true,
        }),
      });
      await load();
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setRegistering(false);
    }
  };

  const autoDiscoverPeers = async () => {
    setDiscovering(true);
    setError(null);
    try {
      const seeds = discoverSeeds
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const request =
        fetchJson ||
        (async (path) => {
          const value = await fetchJsonOptional(path, null);
          if (value == null) throw new Error("request failed");
          return value;
        });
      await request("/api/v1/federation/peers/auto-discover", {
        method: "POST",
        body: JSON.stringify({
          candidate_urls: seeds,
          include_localhost_scan: true,
          max_candidates: 24,
        }),
      });
      await load();
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setDiscovering(false);
    }
  };

  if (loading && !overview) {
    return (
      <div className="mini-card" style={{ marginBottom: 12 }}>
        <strong>Network nodes</strong>
        <p className="proof-layers__meta" style={{ marginTop: 6 }}>
          Loading federation topology…
        </p>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="mini-card" style={{ marginBottom: 12 }}>
        <strong>Network nodes</strong>
        <p className="proof-layers__meta" style={{ marginTop: 6, color: "var(--btc)" }}>
          {error || "Could not load network overview."}
        </p>
        <button type="button" className="btn btn--small" onClick={load}>
          Retry
        </button>
      </div>
    );
  }

  const nodes = overview.nodes || [];
  const satellites = overview.satellites || [];
  const edges = overview.edges || [];
  const local = nodes.find((n) => n.is_local) || nodes[0];
  const peers = nodes.filter((n) => local && n.id !== local.id);

  const width = 480;
  const height = 280;
  const pos = layoutPositions(local, peers, satellites, width, height);

  const edgeColor = (rel) => {
    if (rel === "trusts_peer") return "rgba(247,147,26,0.55)";
    if (rel === "mirrors_remote") return "rgba(167,139,250,0.55)";
    return "rgba(34,211,238,0.50)";
  };

  return (
    <div className="mini-card" style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
        <div>
          <strong>Network nodes</strong>
          <p className="proof-layers__meta" style={{ marginTop: 6 }}>
            PoCP instances (local + peers) and mirrored remote entities. Full Graph tab shows all entity
            types and contribution edges.
          </p>
        </div>
        <button type="button" className="btn btn--small btn--ghost" onClick={load} disabled={loading}>
          {loading ? "…" : "Refresh"}
        </button>
      </div>

      <div className="partner-discover" style={{ marginTop: 8, marginBottom: 10 }}>
        <span className="partner-kind-tag">Nodes: {overview.node_count ?? nodes.length}</span>
        <span className="partner-kind-tag">Peers: {overview.trusted_peer_count ?? peers.length}</span>
        <span className="partner-kind-tag">Mirrors: {overview.mirror_count ?? satellites.length}</span>
        <span className="partner-kind-tag">Trust: {overview.trust_source || "—"}</span>
      </div>

      <form onSubmit={registerPeer} style={{ marginBottom: 10 }}>
        <div className="conn-label">Add peer node now</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 6 }}>
          <input
            type="text"
            placeholder="node_id (e.g. node-b)"
            value={registerNodeId}
            onChange={(e) => setRegisterNodeId(e.target.value)}
            style={{ fontSize: "0.8rem", minWidth: 120 }}
          />
          <input
            type="url"
            placeholder="https://peer.example.com"
            value={registerBaseUrl}
            onChange={(e) => setRegisterBaseUrl(e.target.value)}
            style={{ fontSize: "0.8rem", minWidth: 200, flex: 1 }}
          />
          <button type="submit" className="btn btn--small" disabled={registering}>
            {registering ? "Registering…" : "Register peer"}
          </button>
        </div>
      </form>
      <div style={{ marginBottom: 10 }}>
        <div className="conn-label">Auto discover peers</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 6 }}>
          <input
            type="text"
            placeholder="optional seeds, comma-separated URLs"
            value={discoverSeeds}
            onChange={(e) => setDiscoverSeeds(e.target.value)}
            style={{ fontSize: "0.8rem", minWidth: 280, flex: 1 }}
          />
          <button type="button" className="btn btn--small btn--secondary" disabled={discovering} onClick={autoDiscoverPeers}>
            {discovering ? "Discovering…" : "Auto discover"}
          </button>
        </div>
      </div>

      {overview.setup_hint && (
        <div className="alert alert--info" style={{ marginBottom: 10, fontSize: "0.78rem" }}>
          <strong>No trusted peers configured.</strong> Add to <code>POCP_TRUSTED_NODES</code> in backend
          `.env`, restart backend, then Refresh. Example:{" "}
          <code style={{ wordBreak: "break-all" }}>{overview.setup_hint.example_env}</code>
        </div>
      )}

      <div style={{ overflowX: "auto" }}>
        <svg width={width} height={height} style={{ display: "block", margin: "0 auto" }}>
          <rect x={0} y={0} width={width} height={height} rx={10} fill="rgba(255,255,255,0.02)" />

          {edges.map((e, i) => {
            const a = pos.get(e.source);
            const b = pos.get(e.target);
            if (!a || !b) return null;
            return (
              <line
                key={`${e.source}-${e.target}-${e.relation}-${i}`}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={edgeColor(e.relation)}
                strokeWidth={e.relation === "federated_with" ? 1.6 : 1.1}
                strokeDasharray={e.relation === "mirrors_remote" ? "4 3" : undefined}
                opacity={0.85}
              />
            );
          })}

          {nodes.map((n) => {
            const p = pos.get(n.id);
            if (!p) return null;
            const isLocal = n.is_local;
            const r = isLocal ? 28 : 20;
            return (
              <g
                key={n.id}
                style={{ cursor: onSelectEntity ? "pointer" : "default" }}
                onClick={() => onSelectEntity?.(n.id)}
              >
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={r}
                  fill={isLocal ? "#1a1028" : "#111820"}
                  stroke={isLocal ? "#e879f9" : "rgba(251,113,133,0.9)"}
                  strokeWidth={isLocal ? 2.2 : 1.5}
                />
                <text
                  x={p.x}
                  y={p.y + 4}
                  textAnchor="middle"
                  fontSize={isLocal ? 11 : 8}
                  fill="#e8edf4"
                  fontFamily="JetBrains Mono, monospace"
                >
                  {(n.node_id || n.name || "").length > 14
                    ? `${(n.node_id || n.name).slice(0, 13)}…`
                    : n.node_id || n.name}
                </text>
                <text
                  x={p.x}
                  y={p.y + (isLocal ? 38 : 32)}
                  textAnchor="middle"
                  fontSize={8}
                  fill={isLocal ? "#e879f9" : "rgba(251,113,133,0.85)"}
                  fontFamily="JetBrains Mono, monospace"
                >
                  {isLocal ? "LOCAL" : "PEER"}
                  {(n.mirror_count || 0) > 0 ? ` · ${n.mirror_count} mirrors` : ""}
                </text>
              </g>
            );
          })}

          {satellites.map((s) => {
            const p = pos.get(s.id);
            if (!p) return null;
            return (
              <g
                key={s.id}
                style={{ cursor: onSelectEntity ? "pointer" : "default" }}
                onClick={() => onSelectEntity?.(s.id)}
              >
                <circle cx={p.x} cy={p.y} r={7} fill="#111820" stroke="#a78bfa" strokeWidth={1.2} />
                <title>{s.name}</title>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="conn-muted" style={{ fontSize: "0.72rem", marginTop: 6 }}>
        Large circles = federation nodes · small purple = mirrored remote entities · lines:{" "}
        <span style={{ color: "rgba(34,211,238,0.9)" }}>federated_with</span> ·{" "}
        <span style={{ color: "rgba(167,139,250,0.9)" }}>mirrors_remote</span>
      </div>

      {onRefreshGraph && (
        <button type="button" className="btn btn--small btn--ghost" style={{ marginTop: 8 }} onClick={onRefreshGraph}>
          Open full Graph
        </button>
      )}

      <div
        className="stats-grid"
        style={{ gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", marginTop: 12 }}
      >
        {nodes.map((n) => (
          <button
            key={n.id}
            type="button"
            className="mini-card"
            style={{
              textAlign: "left",
              cursor: "pointer",
              border: "1px solid var(--border-subtle)",
              background: "var(--bg-card)",
            }}
            onClick={() => onSelectEntity?.(n.id)}
          >
            <span className="inspiration-tag">{n.is_local ? "LOCAL" : "PEER"}</span>
            {n.discovered && (
              <span className="remote-tag" style={{ marginLeft: 6 }}>
                DISCOVERED
              </span>
            )}
            {n.inferred_from_mirrors && (
              <span className="remote-tag" style={{ marginLeft: 6 }}>
                FROM MIRRORS
              </span>
            )}
            <strong style={{ display: "block", marginTop: 8 }}>{n.name}</strong>
            <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: 4 }}>
              {n.base_url || "—"}
            </div>
            {(n.mirror_count || 0) > 0 && (
              <div className="entity-row__mission" style={{ marginTop: 6 }}>
                {n.mirror_count} mirrored entit{n.mirror_count === 1 ? "y" : "ies"}
              </div>
            )}
            <div style={{ fontSize: "0.7rem", color: "var(--text-dim)", marginTop: 6 }}>
              id {truncateHash(n.id, 16)}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
