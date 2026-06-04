import { useCallback, useEffect, useState } from "react";
import { API, truncateHash } from "./appShell.js";

async function federationFetch(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json();
}

function layoutPositions(local, peers, satellites, width, height) {
  const cx = width / 2;
  const cy = height / 2;
  const pos = new Map();

  if (local) {
    pos.set(local.id, { x: cx, y: cy, kind: "local" });
  }

  const peerRing = Math.min(120, 60 + peers.length * 16);
  peers.forEach((p, idx) => {
    const angle = (Math.PI * 2 * idx) / Math.max(1, peers.length) - Math.PI / 2;
    pos.set(p.id, {
      x: cx + Math.cos(angle) * peerRing,
      y: cy + Math.sin(angle) * peerRing,
      kind: "peer",
    });
  });

  const satRing = Math.min(175, 95 + Math.min(satellites.length, 24) * 3);
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

function isExternalUrl(url) {
  if (!url) return false;
  return !/localhost|127\.0\.0\.1|host\.docker\.internal/i.test(url);
}

function peerAddrbook(node, addrbookEntry) {
  return (
    node?.last_probe ||
    node?.peer_addrbook ||
    addrbookEntry?.peer_addrbook ||
    node?.metadata?.peer_addrbook ||
    null
  );
}

function formatRelativeTime(iso) {
  if (!iso) return null;
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms)) return iso;
  if (ms < 60_000) return "just now";
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}m ago`;
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)}h ago`;
  return `${Math.floor(ms / 86_400_000)}d ago`;
}

function probeReachability(book) {
  if (!book) return "unknown";
  if (book.banned) return "banned";
  const ok = book.last_success_at;
  const fail = book.last_failure_at;
  if (ok && (!fail || new Date(ok) >= new Date(fail))) return "ok";
  if (fail) return "fail";
  return "unknown";
}

function buildPeerHealth(node, addrbookEntry, sessionHealth) {
  const book = peerAddrbook(node, addrbookEntry);
  const session = sessionHealth || null;
  const sessionProbe = session?.probe || null;
  const reach = probeReachability(book);
  const routable = addrbookEntry?.routable ?? (book && !book.banned);
  const ledgerValid =
    sessionProbe?.ledger_valid ?? book?.ledger_valid ?? (sessionProbe?.reachable ? null : undefined);

  let probeLabel = "Not probed";
  let probeTone = "dim";
  if (reach === "ok") {
    probeLabel = "Reachable";
    probeTone = "ok";
  } else if (reach === "fail") {
    probeLabel = "Unreachable";
    probeTone = "bad";
  } else if (reach === "banned") {
    probeLabel = "Banned";
    probeTone = "bad";
  } else if (sessionProbe?.reachable) {
    probeLabel = "Reachable";
    probeTone = "ok";
  } else if (sessionProbe && !sessionProbe.reachable) {
    probeLabel = "Unreachable";
    probeTone = "bad";
  }

  let dialogueLabel = "Unknown";
  let dialogueTone = "dim";
  if (addrbookEntry != null) {
    if (routable) {
      dialogueLabel = "Routable";
      dialogueTone = "ok";
    } else {
      dialogueLabel = "Blocked";
      dialogueTone = "bad";
    }
  } else if (reach === "ok" || sessionProbe?.reachable) {
    dialogueLabel = "Ready (probe)";
    dialogueTone = "ok";
  }

  let exchangeLabel = "—";
  let exchangeTone = "dim";
  if (ledgerValid === true) {
    exchangeLabel = "Ledger OK";
    exchangeTone = "ok";
  } else if (ledgerValid === false) {
    exchangeLabel = "Ledger invalid";
    exchangeTone = "bad";
  } else if (sessionProbe?.reachable) {
    exchangeLabel = "Surface up";
    exchangeTone = "ok";
  }

  const lastAt = book?.last_success_at || book?.last_failure_at || null;
  const latency = book?.last_latency_ms;

  return {
    book,
    probeLabel,
    probeTone,
    dialogueLabel,
    dialogueTone,
    exchangeLabel,
    exchangeTone,
    lastAt,
    latency,
    lastError: book?.last_error || sessionProbe?.error || null,
    ledgerCount: sessionProbe?.ledger_count,
  };
}

function PeerHealthStrip({ health }) {
  if (!health) return null;
  const toneClass = (tone) => {
    if (tone === "ok") return "inspiration-tag";
    if (tone === "bad") return "remote-tag";
    return "partner-kind-tag";
  };
  return (
    <div style={{ marginTop: 10 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
        <span className={toneClass(health.probeTone)} title="Last federation probe">
          Probe: {health.probeLabel}
        </span>
        <span className={toneClass(health.dialogueTone)} title="Cross-node dialogue route">
          Dialogue: {health.dialogueLabel}
        </span>
        <span className={toneClass(health.exchangeTone)} title="Remote ledger / exchange surface">
          Exchange: {health.exchangeLabel}
        </span>
        {health.latency != null && (
          <span className="partner-kind-tag">{health.latency}ms</span>
        )}
      </div>
      {(health.lastAt || health.lastError) && (
        <div className="proof-layers__meta" style={{ marginTop: 6, fontSize: "0.72rem" }}>
          {health.lastAt && (
            <span>
              Last probe {formatRelativeTime(health.lastAt)}
              {health.ledgerCount != null ? ` · ledger ${health.ledgerCount} rows` : ""}
            </span>
          )}
          {health.lastError && (
            <span style={{ display: "block", color: "var(--btc)", marginTop: 2 }}>
              {health.lastError}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function ConnectHealthBanner({ result }) {
  if (!result) return null;
  const probe = result.probe || result;
  const book = result.peer_addrbook;
  const reachable = result.reachable ?? probe?.reachable;
  if (!reachable && !result.error && !probe?.error) return null;

  const ledgerOk = probe?.ledger_valid;
  const health = book
    ? buildPeerHealth({ metadata: { peer_addrbook: book } }, { peer_addrbook: book, routable: !book.banned }, {
        probe,
      })
    : buildPeerHealth({}, null, { probe });

  return (
    <div className="alert alert--info" style={{ marginBottom: 12, fontSize: "0.82rem" }}>
      <div>
        {reachable ? (
          <>
            Connected to <strong>{result.node_id || probe?.node?.node_id}</strong>
            {result.base_url && <> at {result.base_url}</>}
          </>
        ) : (
          <>Peer unreachable{probe?.error ? `: ${probe.error}` : ""}</>
        )}
        {result.mirror?.mirrored_count != null && (
          <> · mirrored {result.mirror.mirrored_count} entities</>
        )}
      </div>
      {reachable && (
        <div style={{ marginTop: 8 }}>
          <PeerHealthStrip health={health} />
        </div>
      )}
      {ledgerOk === false && (
        <div style={{ marginTop: 6, color: "var(--btc)" }}>
          Remote ledger verification failed — exchange import may be rejected until ledger is valid.
        </div>
      )}
    </div>
  );
}

export default function NetworkNodesPanel({ fetchJson, onSelectEntity, onRefreshGraph }) {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [connectUrl, setConnectUrl] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [connectResult, setConnectResult] = useState(null);
  const [discoverSeeds, setDiscoverSeeds] = useState("");
  const [discovering, setDiscovering] = useState(false);
  const [scanLocal, setScanLocal] = useState(true);
  const [probingId, setProbingId] = useState(null);
  const [mirroringId, setMirroringId] = useState(null);
  const [promotingId, setPromotingId] = useState(null);
  const [addrbookByNodeId, setAddrbookByNodeId] = useState({});
  const [sessionHealthByNodeId, setSessionHealthByNodeId] = useState({});

  const request = useCallback(
    async (path, options) => {
      if (fetchJson) return fetchJson(path, options);
      return federationFetch(path, options);
    },
    [fetchJson]
  );

  const rememberSessionHealth = useCallback((nodeId, payload) => {
    if (!nodeId) return;
    setSessionHealthByNodeId((prev) => ({
      ...prev,
      [nodeId]: {
        probe: payload.probe || payload,
        peer_addrbook: payload.peer_addrbook,
        at: Date.now(),
      },
    }));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [overviewRes, addrbookRes] = await Promise.all([
        federationFetch("/api/v1/federation/network/overview").catch(() => null),
        federationFetch("/api/v1/federation/peers/addrbook").catch(() => null),
      ]);

      const addrMap = {};
      for (const entry of addrbookRes?.peers || []) {
        if (entry?.node_id) addrMap[entry.node_id] = entry;
      }
      setAddrbookByNodeId(addrMap);

      let data = overviewRes;

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
          peer_count: nodes.filter((n) => !n.is_local).length,
          discovered_peer_count: nodes.filter((n) => !n.is_local).length,
          trusted_peer_count: 0,
          mirror_count: 0,
          trust_source: "legacy",
          nodes,
          satellites: [],
          edges,
        };
      }

      setOverview(data);
    } catch (e) {
      setError(String(e.message || e));
      setOverview(null);
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    load();
  }, [load]);

  const connectExternal = async (e) => {
    e.preventDefault();
    const url = connectUrl.trim();
    if (!url) return;
    setConnecting(true);
    setError(null);
    setConnectResult(null);
    try {
      const result = await request("/api/v1/federation/peers/connect", {
        method: "POST",
        body: JSON.stringify({ base_url: url, mirror_entities: true }),
      });
      setConnectResult(result);
      rememberSessionHealth(result.node_id, result);
      setConnectUrl("");
      await load();
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setConnecting(false);
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
      await request("/api/v1/federation/peers/auto-discover", {
        method: "POST",
        body: JSON.stringify({
          candidate_urls: seeds,
          include_localhost_scan: scanLocal,
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

  const probePeer = async (node) => {
    const nodeId = node?.node_id;
    if (!nodeId) return;
    setProbingId(nodeId);
    setError(null);
    try {
      const result = await request(`/api/v1/federation/peers/${encodeURIComponent(nodeId)}/probe`, {
        method: "POST",
      });
      setConnectResult(result);
      rememberSessionHealth(nodeId, result);
      await load();
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setProbingId(null);
    }
  };

  const probePeerByUrl = async (baseUrl) => {
    if (!baseUrl) return;
    setProbingId(baseUrl);
    setError(null);
    try {
      const result = await request("/api/v1/federation/peers/probe", {
        method: "POST",
        body: JSON.stringify({ base_url: baseUrl }),
      });
      setConnectResult(result);
      rememberSessionHealth(result.node_id, result);
      await load();
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setProbingId(null);
    }
  };

  const mirrorPeer = async (nodeId) => {
    if (!nodeId) return;
    setMirroringId(nodeId);
    setError(null);
    try {
      await request(`/api/v1/federation/peers/${encodeURIComponent(nodeId)}/mirror-entities`, {
        method: "POST",
      });
      await load();
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setMirroringId(null);
    }
  };

  const promotePeer = async (nodeId) => {
    if (!nodeId) return;
    setPromotingId(nodeId);
    setError(null);
    try {
      const result = await request(`/api/v1/federation/peers/${encodeURIComponent(nodeId)}/promote-trust`, {
        method: "POST",
      });
      setConnectResult(result);
      await load();
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setPromotingId(null);
    }
  };

  if (loading && !overview) {
    return (
      <section className="panel panel--network">
        <h2 className="panel__title section-heading--ai">Federation Network</h2>
        <p className="panel__subtitle">Loading nodes…</p>
      </section>
    );
  }

  const nodes = overview?.nodes || [];
  const satellites = overview?.satellites || [];
  const edges = overview?.edges || [];
  const local = nodes.find((n) => n.is_local) || nodes[0];
  const peers = nodes.filter((n) => local && n.id !== local.id);
  const peerCount = overview?.peer_count ?? peers.length;
  const discoveredCount = overview?.discovered_peer_count ?? peers.filter((n) => n.discovered).length;

  const width = Math.min(640, typeof window !== "undefined" ? window.innerWidth - 48 : 640);
  const height = 320;
  const pos = layoutPositions(local, peers, satellites, width, height);

  const edgeColor = (rel) => {
    if (rel === "trusts_peer") return "rgba(247,147,26,0.55)";
    if (rel === "mirrors_remote") return "rgba(167,139,250,0.55)";
    return "rgba(34,211,238,0.50)";
  };

  return (
    <section className="panel panel--network">
      <h2 className="panel__title section-heading--ai">Federation Network</h2>
      <p className="panel__subtitle">
        Connect PoCP nodes beyond this machine — LAN IP, public URL, or cloud instance. Discover → probe →
        see dialogue route and exchange (ledger) health per peer — not mirrors alone.
      </p>

      <div className="partner-discover" style={{ marginTop: 8, marginBottom: 12 }}>
        <span className="partner-kind-tag">Nodes: {overview?.node_count ?? nodes.length}</span>
        <span className="partner-kind-tag">Connected: {peerCount}</span>
        <span className="partner-kind-tag">Discovered: {discoveredCount}</span>
        <span className="partner-kind-tag">Mirrors: {overview?.mirror_count ?? satellites.length}</span>
        <span className="partner-kind-tag">Trust: {overview?.trust_source || "—"}</span>
        <button type="button" className="btn btn--small btn--ghost" onClick={load} disabled={loading} style={{ marginLeft: "auto" }}>
          {loading ? "…" : "Refresh"}
        </button>
      </div>

      <form onSubmit={connectExternal} className="mini-card" style={{ marginBottom: 12 }}>
        <strong>Connect external node</strong>
        <p className="proof-layers__meta" style={{ marginTop: 6 }}>
          Enter the peer&apos;s public backend URL. Examples:{" "}
          <code>http://192.168.1.50:8008</code>, <code>https://pocp.example.com</code>
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 10 }}>
          <input
            type="url"
            placeholder="https://remote-pocp.example.com or http://192.168.x.x:8008"
            value={connectUrl}
            onChange={(e) => setConnectUrl(e.target.value)}
            style={{ fontSize: "0.85rem", minWidth: 280, flex: 1 }}
            required
          />
          <button type="submit" className="btn btn--ai" disabled={connecting || !connectUrl.trim()}>
            {connecting ? "Connecting…" : "Connect & mirror"}
          </button>
        </div>
      </form>

      <div className="mini-card" style={{ marginBottom: 12 }}>
        <strong>Auto discover</strong>
        <p className="proof-layers__meta" style={{ marginTop: 6 }}>
          Optional seed URLs (comma-separated). Leave empty to scan configured local ports only.
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8, alignItems: "center" }}>
          <input
            type="text"
            placeholder="http://192.168.1.50:8008, https://peer.example.com"
            value={discoverSeeds}
            onChange={(e) => setDiscoverSeeds(e.target.value)}
            style={{ fontSize: "0.85rem", minWidth: 280, flex: 1 }}
          />
          <label style={{ fontSize: "0.78rem", color: "var(--text-dim)", display: "flex", gap: 6, alignItems: "center" }}>
            <input type="checkbox" checked={scanLocal} onChange={(e) => setScanLocal(e.target.checked)} />
            Scan local ports
          </label>
          <button type="button" className="btn btn--small btn--secondary" disabled={discovering} onClick={autoDiscoverPeers}>
            {discovering ? "Discovering…" : "Auto discover"}
          </button>
        </div>
      </div>

      {error && (
        <div className="alert alert--warn" style={{ marginBottom: 12, fontSize: "0.82rem" }}>
          {error}
        </div>
      )}

      <ConnectHealthBanner result={connectResult} />

      {overview?.setup_hint && peerCount === 0 && (
        <div className="alert alert--info" style={{ marginBottom: 12, fontSize: "0.78rem" }}>
          No peers yet. Use <strong>Connect external node</strong> above, or add trusted peers via{" "}
          <code>POCP_TRUSTED_NODES</code> in backend `.env`.
        </div>
      )}

      <div style={{ overflowX: "auto", marginBottom: 12 }}>
        <svg width={width} height={height} style={{ display: "block", margin: "0 auto" }}>
          <rect x={0} y={0} width={width} height={height} rx={12} fill="rgba(255,255,255,0.02)" stroke="rgba(255,255,255,0.06)" />

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
                strokeWidth={e.relation === "federated_with" ? 2 : 1.2}
                strokeDasharray={e.relation === "mirrors_remote" ? "4 3" : undefined}
                opacity={0.9}
              />
            );
          })}

          {nodes.map((n) => {
            const p = pos.get(n.id);
            if (!p) return null;
            const isLocal = n.is_local;
            const r = isLocal ? 32 : 22;
            const external = isExternalUrl(n.base_url);
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
                  fill={isLocal ? "#1a1028" : external ? "#0f1a14" : "#111820"}
                  stroke={isLocal ? "#e879f9" : external ? "#34d399" : "rgba(251,113,133,0.9)"}
                  strokeWidth={isLocal ? 2.4 : 1.8}
                />
                <text x={p.x} y={p.y + 4} textAnchor="middle" fontSize={isLocal ? 11 : 9} fill="#e8edf4" fontFamily="JetBrains Mono, monospace">
                  {(n.node_id || n.name || "").length > 14 ? `${(n.node_id || n.name).slice(0, 13)}…` : n.node_id || n.name}
                </text>
                <text
                  x={p.x}
                  y={p.y + (isLocal ? 42 : 36)}
                  textAnchor="middle"
                  fontSize={8}
                  fill={isLocal ? "#e879f9" : external ? "#34d399" : "rgba(251,113,133,0.85)"}
                  fontFamily="JetBrains Mono, monospace"
                >
                  {isLocal ? "LOCAL" : external ? "REMOTE" : "PEER"}
                  {(n.mirror_count || 0) > 0 ? ` · ${n.mirror_count}m` : ""}
                </text>
              </g>
            );
          })}

          {satellites.map((s) => {
            const p = pos.get(s.id);
            if (!p) return null;
            return (
              <g key={s.id} style={{ cursor: onSelectEntity ? "pointer" : "default" }} onClick={() => onSelectEntity?.(s.id)}>
                <circle cx={p.x} cy={p.y} r={7} fill="#111820" stroke="#a78bfa" strokeWidth={1.2} />
                <title>{s.name}</title>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="conn-muted" style={{ fontSize: "0.72rem", marginBottom: 12 }}>
        Purple = local · Green = external URL · Pink = local/LAN peer · dashed purple dots = mirrored entities
      </div>

      <div className="stats-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))" }}>
        {nodes.map((n) => (
          <div
            key={n.id}
            className="mini-card"
            style={{ border: "1px solid var(--border-subtle)", background: "var(--bg-card)" }}
          >
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
              <span className="inspiration-tag">{n.is_local ? "LOCAL" : isExternalUrl(n.base_url) ? "REMOTE" : "PEER"}</span>
              {n.discovered && <span className="remote-tag">DISCOVERED</span>}
              {n.peer_banned && <span className="remote-tag" style={{ color: "var(--btc)" }}>BANNED</span>}
              {n.configured && <span className="partner-kind-tag">TRUSTED</span>}
              {n.promoted_trusted && !n.configured && <span className="partner-kind-tag">PROMOTED</span>}
              {n.promotion_eligible && !n.configured && !n.promoted_trusted && (
                <span className="partner-kind-tag" style={{ color: "var(--ai)" }}>
                  ELIGIBLE
                </span>
              )}
              {n.peer_score != null && (
                <span className="partner-kind-tag">score {(n.peer_score * 100).toFixed(0)}%</span>
              )}
            </div>
            <strong style={{ display: "block", marginTop: 8 }}>{n.name}</strong>
            <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: 4, wordBreak: "break-all" }}>
              {n.base_url || "—"}
            </div>
            {(n.mirror_count || 0) > 0 && (
              <div className="entity-row__mission" style={{ marginTop: 6 }}>
                {n.mirror_count} mirrored entit{n.mirror_count === 1 ? "y" : "ies"}
              </div>
            )}
            {!n.is_local && (
              <PeerHealthStrip
                health={buildPeerHealth(
                  n,
                  addrbookByNodeId[n.node_id],
                  sessionHealthByNodeId[n.node_id]
                )}
              />
            )}
            <div style={{ fontSize: "0.7rem", color: "var(--text-dim)", marginTop: 6 }}>
              id {truncateHash(n.id, 16)}
            </div>
            {!n.is_local && (
              <div style={{ display: "flex", gap: 6, marginTop: 10, flexWrap: "wrap" }}>
                <button
                  type="button"
                  className="btn btn--small btn--ghost"
                  disabled={probingId === n.node_id}
                  onClick={() => probePeer(n)}
                >
                  {probingId === n.node_id ? "…" : "Ping"}
                </button>
                <button
                  type="button"
                  className="btn btn--small"
                  disabled={mirroringId === n.node_id}
                  onClick={() => mirrorPeer(n.node_id)}
                >
                  {mirroringId === n.node_id ? "…" : "Mirror entities"}
                </button>
                {n.promotion_eligible && !n.configured && (
                  <button
                    type="button"
                    className="btn btn--small btn--ai"
                    disabled={promotingId === n.node_id}
                    onClick={() => promotePeer(n.node_id)}
                  >
                    {promotingId === n.node_id ? "…" : "Promote trust"}
                  </button>
                )}
                {onSelectEntity && (
                  <button type="button" className="btn btn--small btn--ghost" onClick={() => onSelectEntity(n.id)}>
                    Details
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {onRefreshGraph && (
        <button type="button" className="btn btn--small btn--ghost" style={{ marginTop: 12 }} onClick={onRefreshGraph}>
          Open full Graph
        </button>
      )}
    </section>
  );
}
