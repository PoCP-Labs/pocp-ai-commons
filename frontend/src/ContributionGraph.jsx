import { useMemo } from "react";

const ENTITY_COLORS = {
  human: "#60a5fa",
  agent: "#a78bfa",
  skill: "#34d399",
  organization: "#f7931a",
  llm: "#22d3ee",
};

const RELATION_COLORS = {
  uses: "#60a5fa",
  calls: "#a78bfa",
  invokes_llm: "#22d3ee",
  creator: "#f7931a",
  executor: "#a78bfa",
  skill_provider: "#34d399",
  reviewer: "#fbbf24",
  sponsor: "#f7931a",
};

function layoutNodes(nodes) {
  const byType = {};
  nodes.forEach((n) => {
    if (!byType[n.entity_type]) byType[n.entity_type] = [];
    byType[n.entity_type].push(n);
  });
  const columns = ["human", "agent", "skill", "llm", "organization"];
  const positions = {};
  const colWidth = 168;
  const rowHeight = 76;
  let x = 48;

  columns.forEach((type) => {
    const group = byType[type] || [];
    group.forEach((node, i) => {
      positions[node.id] = { x, y: 48 + i * rowHeight, node };
    });
    if (group.length) x += colWidth;
  });

  Object.entries(byType).forEach(([type, group]) => {
    if (columns.includes(type)) return;
    group.forEach((node, i) => {
      positions[node.id] = { x, y: 48 + i * rowHeight, node };
    });
    x += colWidth;
  });

  return positions;
}

export default function ContributionGraphView({ graph }) {
  const { nodes, edges, positions, width, height } = useMemo(() => {
    if (!graph?.nodes?.length) {
      return { nodes: [], edges: [], positions: {}, width: 640, height: 320 };
    }

    const visibleEdges = graph.edges.filter((e) => !["owns", "created"].includes(e.relation));
    const activeIds = new Set();
    visibleEdges.forEach((e) => {
      activeIds.add(e.source);
      activeIds.add(e.target);
    });
    const activeNodes = graph.nodes.filter((n) => activeIds.has(n.id));
    const pos = layoutNodes(activeNodes);

    const maxX = Math.max(...Object.values(pos).map((p) => p.x), 0) + 140;
    const maxY = Math.max(...Object.values(pos).map((p) => p.y), 0) + 88;

    return {
      nodes: activeNodes,
      edges: visibleEdges,
      positions: pos,
      width: maxX,
      height: maxY,
    };
  }, [graph]);

  if (!nodes.length) {
    return <p className="empty-state">No graph data yet — submit a contribution to grow the network.</p>;
  }

  return (
    <div className="graph-frame">
      <div className="graph-legend">
        {Object.entries(ENTITY_COLORS).map(([type, color]) => (
          <span key={type} className="graph-legend__item">
            <span className="graph-legend__swatch" style={{ background: color }} />
            {type}
          </span>
        ))}
      </div>
      <svg width={width} height={height} style={{ display: "block" }}>
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#22d3ee" opacity="0.7" />
          </marker>
          {Object.entries(ENTITY_COLORS).map(([type, color]) => (
            <filter key={type} id={`glow-${type}`} x="-50%" y="-50%" width="200%" height="200%">
              <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor={color} floodOpacity="0.5" />
            </filter>
          ))}
        </defs>

        {/* Grid dots */}
        {Array.from({ length: Math.ceil(width / 24) }, (_, i) =>
          Array.from({ length: Math.ceil(height / 24) }, (__, j) => (
            <circle key={`${i}-${j}`} cx={i * 24 + 12} cy={j * 24 + 12} r="0.5" fill="rgba(255,255,255,0.04)" />
          ))
        )}

        {edges.map((edge, i) => {
          const from = positions[edge.source];
          const to = positions[edge.target];
          if (!from || !to) return null;
          const x1 = from.x + 108;
          const y1 = from.y + 26;
          const x2 = to.x;
          const y2 = to.y + 26;
          const color = RELATION_COLORS[edge.relation] || "#5c6573";
          const midX = (x1 + x2) / 2;
          const midY = (y1 + y2) / 2 - 12;

          return (
            <g key={i}>
              <line
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={color}
                strokeWidth={1.5}
                strokeOpacity={0.7}
                markerEnd="url(#arrow)"
              />
              <text x={midX} y={midY} textAnchor="middle" fontSize={9} fill="#8b95a5" fontFamily="JetBrains Mono, monospace">
                {edge.relation.replace(/_/g, " ")}
              </text>
            </g>
          );
        })}

        {nodes.map((node) => {
          const pos = positions[node.id];
          if (!pos) return null;
          const color = ENTITY_COLORS[node.entity_type] || "#5c6573";

          return (
            <g key={node.id} transform={`translate(${pos.x}, ${pos.y})`} filter={`url(#glow-${node.entity_type})`}>
              <rect
                width={108}
                height={52}
                rx={8}
                fill="#111820"
                stroke={color}
                strokeWidth={1.5}
              />
              <rect width={108} height={3} rx={8} fill={color} opacity={0.9} />
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
      </svg>
    </div>
  );
}
