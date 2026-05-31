import { useMemo } from "react";

const ENTITY_COLORS = {
  human: "#60a5fa",
  agent: "#a78bfa",
  skill: "#34d399",
  tool: "#facc15",
  dataset: "#2dd4bf",
  workflow: "#fb923c",
  contribution: "#fbbf24",
  ledger: "#94a3b8",
  organization: "#f7931a",
  llm: "#22d3ee",
  community: "#fb7185",
  federation_import: "#c084fc",
};

const RELATION_COLORS = {
  uses: "#60a5fa",
  calls: "#a78bfa",
  invokes_llm: "#22d3ee",
  submits: "#fbbf24",
  verifies: "#22d3ee",
  reviews: "#fbbf24",
  sponsors: "#f7931a",
  creator: "#f7931a",
  executor: "#a78bfa",
  skill_provider: "#34d399",
  reviewer: "#fbbf24",
  verifier: "#22d3ee",
  witness: "#22d3ee",
  sponsor: "#f7931a",
  founded: "#f7931a",
  learned_from: "#fb7185",
  uses_pattern_from: "#fb7185",
  trusts_peer: "#fb7185",
  federated_with: "#fb7185",
  hosts: "#f7931a",
  seeks_partnership: "#34d399",
  partners_with: "#34d399",
  offers_capability: "#34d399",
  integrates: "#a78bfa",
  exported_contribution: "#c084fc",
  imported_to: "#c084fc",
  received_import: "#c084fc",
  final_review: "#fbbf24",
  witnesses: "#22d3ee",
  recorded_in: "#94a3b8",
  provides_tool: "#64748b",
  provides_data: "#64748b",
};

const LAYOUT_COLUMNS = [
  "human",
  "agent",
  "skill",
  "tool",
  "dataset",
  "workflow",
  "contribution",
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

/**
 * Merge entity registry with graph metrics so every registered entity appears on the canvas.
 */
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
  const { entityNodes, hubNodes, visibleEdges, positions, width, height, connectedIds } = useMemo(() => {
    const entityNodes = buildEntityNodes(entities, graph);
    const hubNodes = (graph?.nodes || []).filter(
      (n) =>
        n.entity_type === "contribution" ||
        n.entity_type === "federation_import" ||
        n.entity_type === "ledger"
    );
    const visibleEdges = (graph?.edges || []).filter((e) => !["owns", "created"].includes(e.relation));

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
    };
  }, [graph, entities]);

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
        · {visibleEdges.length} relation{visibleEdges.length === 1 ? "" : "s"}
      </p>
      <div className="graph-legend">
        {Object.entries(ENTITY_COLORS).map(([type, color]) => (
          <span key={type} className="graph-legend__item">
            <span className="graph-legend__swatch" style={{ background: color }} />
            {type}
          </span>
        ))}
        <span className="graph-legend__item" style={{ opacity: 0.7 }}>
          dashed = registered, no relation edge yet
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
          const color = RELATION_COLORS[edge.relation] || "#5c6573";
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
            <g key={edgeKey} className="graph-edge">
              <path
                className="graph-edge__track"
                d={pathD}
                fill="none"
                stroke={color}
                strokeWidth={0.75}
                strokeOpacity={0.28}
                strokeDasharray="3 5"
                strokeLinecap="round"
                style={{ animationDelay: `${marchDelay}s` }}
              />
              {Array.from({ length: dotCount }, (_, di) => {
                const begin = (travelSec / dotCount) * di;
                return (
                  <circle
                    key={`${edgeKey}-dot-${di}`}
                    r={2}
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
              <circle
                key={`${edgeKey}-dot-reverse`}
                r={1.4}
                fill={color}
                opacity={0.45}
                filter="url(#graph-pulse-dot)"
              >
                <animateMotion
                  dur={`${reverseTravelSec}s`}
                  begin={`${travelSec * 0.45}s`}
                  repeatCount="indefinite"
                  path={reversePathD}
                />
              </circle>
              <text x={midX} y={midY} textAnchor="middle" fontSize={8} fill="#6b7585" fontFamily="JetBrains Mono, monospace">
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
          const color = ENTITY_COLORS[node.entity_type] || ENTITY_COLORS.contribution;

          return (
            <g
              key={node.id}
              transform={`translate(${pos.x}, ${pos.y})`}
              filter={`url(#glow-${node.entity_type === "federation_import" ? "federation_import" : node.entity_type === "ledger" ? "ledger" : "contribution"})`}
            >
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
                {node.entity_type === "federation_import"
                  ? "FED IMPORT"
                  : node.entity_type === "ledger"
                    ? "LEDGER"
                    : "CONTRIBUTION"}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
