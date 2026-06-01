import { useMemo, useState } from "react";

const ENTITY_COLORS = {
  human: "#60a5fa",
  agent: "#a78bfa",
  skill: "#34d399",
  tool: "#facc15",
  dataset: "#2dd4bf",
  workflow: "#fb923c",
  contribution: "#fbbf24",
  ledger: "#94a3b8",
  exchange: "#64748b",
  organization: "#f7931a",
  llm: "#22d3ee",
  community: "#fb7185",
  federation_import: "#c084fc",
};

/** Protocol connection layers — aligned with docs/protocol/ENTITY-CONNECTION.md */
export const CONNECTION_LAYERS = [
  { id: "structural", label: "Structural", labelZh: "结构层", color: "#f7931a" },
  { id: "protocol", label: "Protocol", labelZh: "贡献协议", color: "#fbbf24" },
  { id: "operational", label: "Operational", labelZh: "运行迹", color: "#22d3ee" },
];

const LAYER_BY_ID = Object.fromEntries(CONNECTION_LAYERS.map((l) => [l.id, l]));

const STRUCTURAL_RELATIONS = new Set(["owns", "created", "founded"]);
const OPERATIONAL_RELATIONS = new Set([
  "uses",
  "calls",
  "invokes_llm",
  "invokes_mcp",
  "hosts_inference",
  "hosts",
]);

export function resolveConnectionLayer(edge) {
  if (edge?.connection_layer && LAYER_BY_ID[edge.connection_layer]) {
    return edge.connection_layer;
  }
  const rel = edge?.relation || "";
  if (STRUCTURAL_RELATIONS.has(rel)) return "structural";
  if (OPERATIONAL_RELATIONS.has(rel)) return "operational";
  return "protocol";
}

const LAYOUT_COLUMNS = [
  "human",
  "agent",
  "skill",
  "tool",
  "dataset",
  "workflow",
  "contribution",
  "exchange",
  "ledger",
  "federation_import",
  "llm",
  "organization",
  "community",
];

function edgePath(x1, y1, x2, y2) {
  return `M ${x1} ${y1} L ${x2} ${y2}`;
}

function reverseEdgePath(x1, y1, x2, y2) {
  return `M ${x2} ${y2} L ${x1} ${y1}`;
}

function edgeTravelSeconds(x1, y1, x2, y2) {
  const dist = Math.hypot(x2 - x1, y2 - y1);
  return Math.max(1.6, dist / 48);
}

function pulseDotCount(x1, y1, x2, y2) {
  const dist = Math.hypot(x2 - x1, y2 - y1);
  if (dist < 120) return 2;
  if (dist < 220) return 3;
  return 4;
}

function layerStrokeStyle(layerId) {
  switch (layerId) {
    case "structural":
      return { strokeWidth: 1, strokeOpacity: 0.42, strokeDasharray: undefined };
    case "operational":
      return { strokeWidth: 1.35, strokeOpacity: 0.55, strokeDasharray: undefined };
    default:
      return { strokeWidth: 0.85, strokeOpacity: 0.32, strokeDasharray: "4 5" };
  }
}

function layoutNodes(nodes) {
  const byType = {};
  nodes.forEach((n) => {
    if (!byType[n.entity_type]) byType[n.entity_type] = [];
    byType[n.entity_type].push(n);
  });
  const positions = {};
  const colWidth = 168;
  const rowHeight = 76;
  let x = 48;

  LAYOUT_COLUMNS.forEach((type) => {
    const group = byType[type] || [];
    group.forEach((node, i) => {
      positions[node.id] = { x, y: 48 + i * rowHeight, node };
    });
    if (group.length) x += colWidth;
  });

  Object.entries(byType).forEach(([type, group]) => {
    if (LAYOUT_COLUMNS.includes(type)) return;
    group.forEach((node, i) => {
      positions[node.id] = { x, y: 48 + i * rowHeight, node };
    });
    x += colWidth;
  });

  return positions;
}

function buildEntityNodes(entities, graph) {
  const graphById = Object.fromEntries(
    (graph?.nodes || [])
      .filter((n) => n.entity_type !== "contribution")
      .map((n) => [n.id, n])
  );
  return (entities || []).map((e) => {
    const g = graphById[e.id];
    return {
      id: e.id,
      entity_type: e.entity_type,
      name: e.name,
      reputation: g?.reputation ?? 0,
      cp_balance: g?.cp_balance ?? 0,
      ai_credits: g?.ai_credits ?? 0,
    };
  });
}

export default function ContributionGraphView({ graph, entities = [] }) {
  const [activeLayers, setActiveLayers] = useState(() =>
    Object.fromEntries(CONNECTION_LAYERS.map((l) => [l.id, true]))
  );

  const toggleLayer = (layerId) => {
    setActiveLayers((prev) => {
      const next = { ...prev, [layerId]: !prev[layerId] };
      if (!CONNECTION_LAYERS.some((l) => next[l.id])) {
        return prev;
      }
      return next;
    });
  };

  const { entityNodes, hubNodes, visibleEdges, positions, width, height, connectedIds, layerCounts } =
    useMemo(() => {
      const entityNodes = buildEntityNodes(entities, graph);
      const hubNodes = (graph?.nodes || []).filter(
        (n) =>
          n.entity_type === "contribution" ||
          n.entity_type === "federation_import" ||
          n.entity_type === "ledger" ||
          n.entity_type === "exchange"
      );

      const allEdges = (graph?.edges || []).map((e) => ({
        ...e,
        connection_layer: resolveConnectionLayer(e),
      }));

      const counts = { structural: 0, protocol: 0, operational: 0 };
      allEdges.forEach((e) => {
        counts[e.connection_layer] = (counts[e.connection_layer] || 0) + 1;
      });

      const visibleEdges = allEdges.filter((e) => activeLayers[e.connection_layer]);

      const connectedIds = new Set();
      visibleEdges.forEach((e) => {
        connectedIds.add(e.source);
        connectedIds.add(e.target);
      });

      const allLayoutNodes = [...entityNodes, ...hubNodes];
      const pos = layoutNodes(allLayoutNodes);

      const maxX = Math.max(...Object.values(pos).map((p) => p.x), 0) + 140;
      const maxY = Math.max(...Object.values(pos).map((p) => p.y), 0) + 88;

      return {
        entityNodes,
        hubNodes,
        visibleEdges,
        positions: pos,
        width: maxX,
        height: maxY,
        connectedIds,
        layerCounts: graph?.edge_layer_counts || counts,
      };
    }, [graph, entities, activeLayers]);

  const entityCount = entities.length;
  const hubCount = hubNodes.length;

  if (!entityCount) {
    return <p className="empty-state">No entities yet — start the backend to seed the demo network.</p>;
  }

  return (
    <div className="graph-frame">
      <p className="panel__subtitle graph-frame__subtitle">
        Contribution neural network — {entityCount} entities · {hubCount} hub{hubCount === 1 ? "" : "s"}
        {graph?.ledger_node_count != null && graph.ledger_node_count > 0
          ? ` · ${graph.ledger_node_count} ledger`
          : ""}{" "}
        · {visibleEdges.length} edge{visibleEdges.length === 1 ? "" : "s"} shown
      </p>

      <div className="graph-layer-controls">
        <span className="graph-layer-controls__title">Connection layers</span>
        {CONNECTION_LAYERS.map((layer) => {
          const on = activeLayers[layer.id];
          const count = layerCounts[layer.id] ?? 0;
          return (
            <button
              key={layer.id}
              type="button"
              className={`graph-layer-toggle${on ? " graph-layer-toggle--active" : ""}`}
              onClick={() => toggleLayer(layer.id)}
              title={graph?.connection_layers?.[layer.id] || layer.label}
            >
              <span className="graph-layer-toggle__swatch" style={{ background: layer.color }} />
              {layer.label}
              <span className="graph-layer-toggle__zh">{layer.labelZh}</span>
              <span className="graph-layer-toggle__count">{count}</span>
            </button>
          );
        })}
      </div>

      <div className="graph-legend">
        {Object.entries(ENTITY_COLORS).map(([type, color]) => (
          <span key={type} className="graph-legend__item">
            <span className="graph-legend__swatch" style={{ background: color }} />
            {type}
          </span>
        ))}
        <span className="graph-legend__item" style={{ opacity: 0.7 }}>
          dashed outline = registered, no visible edge in active layers
        </span>
      </div>

      <svg width={width} height={height} style={{ display: "block" }}>
        <defs>
          <filter id="graph-pulse-dot" x="-200%" y="-200%" width="500%" height="500%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="1.2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          {Object.entries(ENTITY_COLORS).map(([type, color]) => (
            <filter key={type} id={`glow-${type}`} x="-50%" y="-50%" width="200%" height="200%">
              <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor={color} floodOpacity="0.5" />
            </filter>
          ))}
        </defs>

        {Array.from({ length: Math.ceil(width / 24) }, (_, i) =>
          Array.from({ length: Math.ceil(height / 24) }, (__, j) => (
            <circle key={`${i}-${j}`} cx={i * 24 + 12} cy={j * 24 + 12} r="0.5" fill="rgba(255,255,255,0.04)" />
          ))
        )}

        {visibleEdges.map((edge, i) => {
          const from = positions[edge.source];
          const to = positions[edge.target];
          if (!from || !to) return null;
          const x1 = from.x + 108;
          const y1 = from.y + 26;
          const x2 = to.x;
          const y2 = to.y + 26;
          const layer = LAYER_BY_ID[edge.connection_layer] || LAYER_BY_ID.protocol;
          const color = layer.color;
          const stroke = layerStrokeStyle(edge.connection_layer);
          const pathD = edgePath(x1, y1, x2, y2);
          const reversePathD = reverseEdgePath(x1, y1, x2, y2);
          const travelSec = edgeTravelSeconds(x1, y1, x2, y2);
          const reverseTravelSec = travelSec * 1.35;
          const dotCount = pulseDotCount(x1, y1, x2, y2);
          const marchDelay = (i * 0.18) % 2.4;
          const midX = (x1 + x2) / 2;
          const midY = (y1 + y2) / 2 - 12;
          const label = edge.relation.replace(/_/g, " ");
          const edgeKey = `${edge.source}-${edge.target}-${edge.relation}-${i}`;

          return (
            <g key={edgeKey} className={`graph-edge graph-edge--${edge.connection_layer}`}>
              <path
                className="graph-edge__track"
                d={pathD}
                fill="none"
                stroke={color}
                strokeWidth={stroke.strokeWidth}
                strokeOpacity={stroke.strokeOpacity}
                strokeDasharray={stroke.strokeDasharray}
                strokeLinecap="round"
                style={{ animationDelay: `${marchDelay}s` }}
              />
              {Array.from({ length: dotCount }, (_, di) => {
                const begin = (travelSec / dotCount) * di;
                return (
                  <circle
                    key={`${edgeKey}-dot-${di}`}
                    r={edge.connection_layer === "operational" ? 2.4 : 2}
                    fill={color}
                    opacity={0.92}
                    filter="url(#graph-pulse-dot)"
                  >
                    <animateMotion
                      dur={`${travelSec}s`}
                      begin={`${begin}s`}
                      repeatCount="indefinite"
                      path={pathD}
                    />
                  </circle>
                );
              })}
              <circle r={1.4} fill={color} opacity={0.45} filter="url(#graph-pulse-dot)">
                <animateMotion
                  dur={`${reverseTravelSec}s`}
                  begin={`${travelSec * 0.45}s`}
                  repeatCount="indefinite"
                  path={reversePathD}
                />
              </circle>
              <text
                x={midX}
                y={midY}
                textAnchor="middle"
                fontSize={8}
                fill={color}
                fillOpacity={0.85}
                fontFamily="JetBrains Mono, monospace"
              >
                {label}
              </text>
            </g>
          );
        })}

        {entityNodes.map((node) => {
          const pos = positions[node.id];
          if (!pos) return null;
          const color = ENTITY_COLORS[node.entity_type] || "#5c6573";
          const isolated = !connectedIds.has(node.id);

          return (
            <g key={node.id} transform={`translate(${pos.x}, ${pos.y})`} filter={`url(#glow-${node.entity_type})`}>
              <rect
                width={108}
                height={52}
                rx={8}
                fill="#111820"
                stroke={color}
                strokeWidth={1.5}
                strokeDasharray={isolated ? "4 3" : undefined}
                opacity={isolated ? 0.75 : 1}
              />
              <rect width={108} height={3} rx={8} fill={color} opacity={isolated ? 0.5 : 0.9} />
              <text
                x={54}
                y={24}
                textAnchor="middle"
                fontSize={11}
                fontWeight="600"
                fill="#e8edf4"
                fontFamily="DM Sans, sans-serif"
              >
                {node.name.length > 14 ? `${node.name.slice(0, 13)}…` : node.name}
              </text>
              <text
                x={54}
                y={40}
                textAnchor="middle"
                fontSize={8}
                fill={color}
                fontFamily="JetBrains Mono, monospace"
                letterSpacing="0.08em"
              >
                {node.entity_type.toUpperCase()}
              </text>
            </g>
          );
        })}

        {hubNodes.map((node) => {
          const pos = positions[node.id];
          if (!pos) return null;
          const glowType =
            node.entity_type === "federation_import"
              ? "federation_import"
              : node.entity_type === "ledger"
                ? "ledger"
                : node.entity_type === "exchange"
                  ? "exchange"
                  : "contribution";
          const color = ENTITY_COLORS[node.entity_type] || ENTITY_COLORS.contribution;
          const hubLabel =
            node.entity_type === "federation_import"
              ? "FED IMPORT"
              : node.entity_type === "ledger"
                ? "LEDGER"
                : node.entity_type === "exchange"
                  ? "EXCHANGE"
                  : "CONTRIBUTION";

          return (
            <g key={node.id} transform={`translate(${pos.x}, ${pos.y})`} filter={`url(#glow-${glowType})`}>
              <rect width={108} height={52} rx={8} fill="#111820" stroke={color} strokeWidth={1.5} />
              <rect width={108} height={3} rx={8} fill={color} opacity={0.9} />
              <text
                x={54}
                y={24}
                textAnchor="middle"
                fontSize={10}
                fontWeight="600"
                fill="#e8edf4"
                fontFamily="DM Sans, sans-serif"
              >
                {node.name.length > 14 ? `${node.name.slice(0, 13)}…` : node.name}
              </text>
              <text
                x={54}
                y={40}
                textAnchor="middle"
                fontSize={8}
                fill={color}
                fontFamily="JetBrains Mono, monospace"
                letterSpacing="0.08em"
              >
                {hubLabel}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
