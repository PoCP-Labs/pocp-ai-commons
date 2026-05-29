import { useMemo } from "react";

const ENTITY_COLORS = {
  human: "#2563eb",
  agent: "#7c3aed",
  skill: "#059669",
  organization: "#d97706",
  llm: "#64748b",
};

const RELATION_COLORS = {
  uses: "#3b82f6",
  calls: "#8b5cf6",
  invokes_llm: "#94a3b8",
  creator: "#2563eb",
  executor: "#7c3aed",
  skill_provider: "#059669",
  reviewer: "#f59e0b",
  sponsor: "#d97706",
};

function layoutNodes(nodes, edges) {
  const byType = {};
  nodes.forEach((n) => {
    if (!byType[n.entity_type]) byType[n.entity_type] = [];
    byType[n.entity_type].push(n);
  });
  const columns = ["human", "agent", "skill", "llm", "organization"];
  const positions = {};
  const colWidth = 160;
  const rowHeight = 72;
  let x = 40;

  columns.forEach((type) => {
    const group = byType[type] || [];
    group.forEach((node, i) => {
      positions[node.id] = { x, y: 40 + i * rowHeight, node };
    });
    if (group.length) x += colWidth;
  });

  Object.entries(byType).forEach(([type, group]) => {
    if (columns.includes(type)) return;
    group.forEach((node, i) => {
      positions[node.id] = { x, y: 40 + i * rowHeight, node };
    });
    x += colWidth;
  });

  return positions;
}

export default function ContributionGraphView({ graph, entityMap }) {
  const { nodes, edges, positions, width, height } = useMemo(() => {
    if (!graph?.nodes?.length) {
      return { nodes: [], edges: [], positions: {}, width: 600, height: 300 };
    }

    const visibleEdges = graph.edges.filter(
      (e) => !["owns", "created"].includes(e.relation)
    );
    const activeIds = new Set();
    visibleEdges.forEach((e) => {
      activeIds.add(e.source);
      activeIds.add(e.target);
    });
    const activeNodes = graph.nodes.filter((n) => activeIds.has(n.id));
    const pos = layoutNodes(activeNodes, visibleEdges);

    const maxX = Math.max(...Object.values(pos).map((p) => p.x), 0) + 120;
    const maxY = Math.max(...Object.values(pos).map((p) => p.y), 0) + 80;

    return {
      nodes: activeNodes,
      edges: visibleEdges,
      positions: pos,
      width: maxX,
      height: maxY,
    };
  }, [graph]);

  if (!nodes.length) {
    return <p style={{ color: "#64748b" }}>No graph data yet.</p>;
  }

  return (
    <div style={{ overflow: "auto", border: "1px solid #e2e8f0", borderRadius: 8, background: "#fff" }}>
      <svg width={width} height={height} style={{ display: "block" }}>
        <defs>
          <marker
            id="arrow"
            viewBox="0 0 10 10"
            refX="10"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8" />
          </marker>
        </defs>

        {edges.map((edge, i) => {
          const from = positions[edge.source];
          const to = positions[edge.target];
          if (!from || !to) return null;
          const x1 = from.x + 100;
          const y1 = from.y + 22;
          const x2 = to.x;
          const y2 = to.y + 22;
          const color = RELATION_COLORS[edge.relation] || "#cbd5e1";
          const midX = (x1 + x2) / 2;
          const midY = (y1 + y2) / 2 - 10;

          return (
            <g key={i}>
              <line
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={color}
                strokeWidth={1.5}
                markerEnd="url(#arrow)"
              />
              <text x={midX} y={midY} textAnchor="middle" fontSize={10} fill="#64748b">
                {edge.relation.replace(/_/g, " ")}
              </text>
            </g>
          );
        })}

        {nodes.map((node) => {
          const pos = positions[node.id];
          if (!pos) return null;
          const color = ENTITY_COLORS[node.entity_type] || "#64748b";

          return (
            <g key={node.id} transform={`translate(${pos.x}, ${pos.y})`}>
              <rect
                width={100}
                height={44}
                rx={6}
                fill={color}
                opacity={0.12}
                stroke={color}
                strokeWidth={1.5}
              />
              <text x={50} y={18} textAnchor="middle" fontSize={11} fontWeight="600" fill="#1e293b">
                {node.name.length > 12 ? node.name.slice(0, 11) + "…" : node.name}
              </text>
              <text x={50} y={34} textAnchor="middle" fontSize={9} fill="#64748b">
                {node.entity_type}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
