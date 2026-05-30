import { useMemo } from "react";

const ENTITY_COLORS = {
  human: "#2563eb",
  agent: "#7c3aed",
  skill: "#059669",
  organization: "#d97706",
  llm: "#64748b",
};

const PROCESS_COLORS = {
  contribution: "#0891b2",
  ai_verifier: "#8b5cf6",
  human_reviewer: "#f59e0b",
  ledger: "#be185d",
};

const RELATION_COLORS = {
  use: "#3b82f6",
  uses: "#3b82f6",
  calls: "#8b5cf6",
  invokes_llm: "#94a3b8",
  creator: "#2563eb",
  executor: "#7c3aed",
  skill_provider: "#059669",
  reviewer: "#f59e0b",
  sponsor: "#d97706",
  owns: "#94a3b8",
  created: "#94a3b8",
  submitted: "#0891b2",
  ai_verified: "#8b5cf6",
  approved: "#f59e0b",
  recorded: "#be185d",
};

function typeColor(node) {
  if (node.nodeType === "process") return PROCESS_COLORS[node.processType] || "#64748b";
  return ENTITY_COLORS[node.entity_type] || "#64748b";
}

function layoutNodes(nodes) {
  // Group nodes by type and layout in columns
  const entityTypes = ["human", "agent", "skill", "organization", "llm"];
  const processTypes = ["contribution", "ai_verifier", "human_reviewer", "ledger"];

  const columns = [
    { key: "entity:human", label: "Humans" },
    { key: "entity:agent", label: "Agents" },
    { key: "entity:skill", label: "Skills" },
    { key: "process:contribution", label: "Contributions" },
    { key: "process:ai_verifier", label: "AI Verifiers" },
    { key: "process:human_reviewer", label: "Human Reviews" },
    { key: "entity:organization", label: "Orgs" },
    { key: "process:ledger", label: "Ledger" },
    { key: "entity:llm", label: "LLMs" },
  ];

  // Assign each node to a column
  const columnNodes = columns.map(() => []);
  const positions = {};
  const colWidth = 140;
  const rowHeight = 64;

  // Entity node dimensions
  const entityWidth = 110;
  const entityHeight = 44;

  // Process node dimensions
  const processWidth = 130;
  const processHeight = 36;

  nodes.forEach((node) => {
    let colIndex = -1;
    if (node.nodeType === "process") {
      colIndex = columns.findIndex((c) => c.key === `process:${node.processType}`);
    } else {
      colIndex = columns.findIndex((c) => c.key === `entity:${node.entity_type}`);
    }
    if (colIndex >= 0) columnNodes[colIndex].push(node);
  });

  let x = 30;
  columns.forEach((col, i) => {
    const group = columnNodes[i];
    if (group.length === 0) return;

    group.forEach((node, j) => {
      const isProcess = node.nodeType === "process";
      const w = isProcess ? processWidth : entityWidth;
      const h = isProcess ? processHeight : entityHeight;
      positions[node.id] = {
        x,
        y: 50 + j * rowHeight,
        width: w,
        height: h,
        node,
      };
    });

    // Add column header space
    x += colWidth;
  });

  // Find any nodes not in columns (unknown types)
  const unknownNodes = nodes.filter((n) => !(n.id in positions));
  unknownNodes.forEach((node, i) => {
    positions[node.id] = {
      x,
      y: 50 + i * rowHeight,
      width: 100,
      height: 44,
      node,
    };
    if (i === 0) x += colWidth;
  });

  return positions;
}

export default function ContributionGraphView({
  graph,
  entityMap,
  contributions = [],
  ledger = [],
}) {
  const { nodes, edges, positions, width, height } = useMemo(() => {
    if (!graph?.nodes?.length && !contributions?.length) {
      return { nodes: [], edges: [], positions: {}, width: 600, height: 300 };
    }

    // Step 1: Start with entity nodes from graph
    const entityNodes = (graph.nodes || []).map((n) => ({
      ...n,
      nodeType: "entity",
    }));

    // Build a ledger lookup by contribution_id
    const ledgerByContrib = {};
    (ledger || []).forEach((l) => {
      if (l.contribution_id) {
        if (!ledgerByContrib[l.contribution_id]) ledgerByContrib[l.contribution_id] = [];
        ledgerByContrib[l.contribution_id].push(l);
      }
    });

    // Step 2: Add Contribution process nodes
    const contributionNodes = (contributions || []).map((c) => ({
      id: `contrib:${c.id}`,
      nodeType: "process",
      processType: "contribution",
      name: c.description?.slice(0, 24) || "Contribution",
      label: c.contribution_type || "contribution",
      status: c.status,
      entity_type: c.contribution_type || "contribution",
      subtext: `${c.status}`,
      ledger_entries: ledgerByContrib[c.id] || [],
    }));

    // Step 3: Add AI Verifier nodes
    const processedVerifiers = new Set();
    const verifierNodes = [];
    (contributions || []).forEach((c) => {
      (c.ai_verifications || []).forEach((v) => {
        const nid = `verifier:${v.id || `${c.id}-${v.model_provider}`}`;
        if (processedVerifiers.has(nid)) return;
        processedVerifiers.add(nid);
        verifierNodes.push({
          id: nid,
          nodeType: "process",
          processType: "ai_verifier",
          name: v.model_provider || "AI Verifier",
          label: `score: ${v.score?.toFixed(2) || "?"}`,
          subtext: v.passed ? "passed ✓" : "flagged ⚠",
          score: v.score || 0,
          passed: v.passed,
        });
      });
    });

    // Step 4: Add Human Reviewer nodes
    const reviewerNodes = [];
    (contributions || []).forEach((c) => {
      (c.human_reviews || []).forEach((r) => {
        const reviewerName = entityMap[r.reviewer_id]?.name || "Reviewer";
        reviewerNodes.push({
          id: `review:${r.id || `${c.id}-${r.reviewer_id}`}`,
          nodeType: "process",
          processType: "human_reviewer",
          name: `Human: ${reviewerName}`,
          label: r.approved ? "approved ✓" : "rejected ✗",
          subtext: r.feedback?.slice(0, 30) || "",
          approved: r.approved,
        });
      });
    });

    // Step 5: Add Ledger nodes
    const ledgerNodeIds = new Set();
    const ledgerNodes = [];
    (contributions || []).forEach((c) => {
      (c.ledger_entries || []).forEach((l) => {
        if (ledgerNodeIds.has(`ledger:${l.id || c.id}`)) return;
        ledgerNodeIds.add(`ledger:${l.id || c.id}`);
        ledgerNodes.push({
          id: `ledger:${l.id || c.id}`,
          nodeType: "process",
          processType: "ledger",
          name: "Ledger",
          label: l.event_type || "recorded",
          subtext: new Date(l.created_at || c.created_at).toLocaleDateString(),
        });
      });
    });

    // Combine all nodes
    const allNodes = [...entityNodes, ...contributionNodes, ...verifierNodes, ...reviewerNodes, ...ledgerNodes];

    // Step 6: Build edges connecting process nodes
    const contribEdgeMap = new Map();

    // Existing entity edges
    const baseEdges = (graph.edges || []).filter(
      (e) => !["owns", "created"].includes(e.relation)
    ).map((e) => ({ ...e }));

    // Add edges: entity → contribution
    (contributions || []).forEach((c) => {
      const contribNodeId = `contrib:${c.id}`;
      
      // Entity participants → contribution
      (c.participants || []).forEach((p) => {
        if (entityMap[p.entity_id]) {
          baseEdges.push({
            source: p.entity_id,
            target: contribNodeId,
            relation: "submitted",
            weight: p.weight,
          });
        }
      });

      // Contribution → AI Verifier
      (c.ai_verifications || []).forEach((v) => {
        const verNodeId = `verifier:${v.id || `${c.id}-${v.model_provider}`}`;
        baseEdges.push({
          source: contribNodeId,
          target: verNodeId,
          relation: "ai_verified",
          weight: v.score || 0.5,
        });
      });

      // Contribution → Human Reviewer
      (c.human_reviews || []).forEach((r) => {
        const revNodeId = `review:${r.id || `${c.id}-${r.reviewer_id}`}`;
        baseEdges.push({
          source: contribNodeId,
          target: revNodeId,
          relation: "approved",
          weight: r.approved ? 1 : 0,
        });
        // Reviewer → Human entity
        if (entityMap[r.reviewer_id]) {
          baseEdges.push({
            source: revNodeId,
            target: r.reviewer_id,
            relation: "reviewer",
            weight: 1,
          });
        }
      });

      // Contribution → Ledger
      (c.ledger_entries || []).forEach((l) => {
        const ledgerNodeId = `ledger:${l.id || c.id}`;
        baseEdges.push({
          source: contribNodeId,
          target: ledgerNodeId,
          relation: "recorded",
          weight: 1,
        });
      });
    });

    const pos = layoutNodes(allNodes);
    const maxX = Math.max(...Object.values(pos).map((p) => p.x + (p.width || 110)), 0) + 40;
    const maxY = Math.max(...Object.values(pos).map((p) => p.y + (p.height || 44)), 0) + 80;

    return {
      nodes: allNodes,
      edges: baseEdges,
      positions: pos,
      width: Math.max(maxX, 600),
      height: Math.max(maxY, 300),
    };
  }, [graph, entityMap, contributions, aiVerifiers, humanReviews, ledgerRecords]);

  if (!nodes.length) {
    return (
      <p style={{ color: "#64748b" }}>
        No graph data yet. Submit a contribution to see the flow.
      </p>
    );
  }

  return (
    <div
      style={{
        overflow: "auto",
        border: "1px solid #e2e8f0",
        borderRadius: 8,
        background: "#fff",
      }}
    >
      {/* Legend */}
      <div
        style={{
          display: "flex",
          gap: 16,
          padding: "8px 16px",
          borderBottom: "1px solid #e2e8f0",
          fontSize: 12,
          flexWrap: "wrap",
        }}
      >
        {Object.entries({ ...ENTITY_COLORS, ...PROCESS_COLORS }).map(
          ([type, color]) => (
            <span key={type} style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: 2,
                  background: color,
                  display: "inline-block",
                }}
              />
              {type.replace(/_/g, " ")}
            </span>
          )
        )}
      </div>

      <svg width={width} height={height} style={{ display: "block" }}>
        <defs>
          <marker
            id="arrow2"
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

        {/* Edges */}
        {edges.map((edge, i) => {
          const from = positions[edge.source];
          const to = positions[edge.target];
          if (!from || !to) return null;

          const x1 = from.x + (from.width || 110);
          const y1 = from.y + (from.height || 44) / 2;
          const x2 = to.x;
          const y2 = to.y + (to.height || 44) / 2;
          const color = RELATION_COLORS[edge.relation] || "#cbd5e1";
          const midX = (x1 + x2) / 2;
          const midY = (y1 + y2) / 2 - 8;

          // Weighted line width
          const strokeWidth = edge.weight ? Math.max(1, Math.min(3, edge.weight * 3)) : 1;

          return (
            <g key={`edge-${i}`}>
              <line
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={color}
                strokeWidth={strokeWidth}
                strokeOpacity={0.6}
                markerEnd="url(#arrow2)"
              />
              {edge.weight && (
                <text
                  x={midX}
                  y={midY}
                  textAnchor="middle"
                  fontSize={9}
                  fill="#64748b"
                  style={{ opacity: 0.7 }}
                >
                  {edge.relation.replace(/_/g, " ")}
                </text>
              )}
            </g>
          );
        })}

        {/* Nodes */}
        {nodes.map((node) => {
          const pos = positions[node.id];
          if (!pos) return null;

          const isProcess = node.nodeType === "process";
          const w = pos.width || 110;
          const h = pos.height || 44;
          const color = typeColor(node);
          const bgOpacity = isProcess ? 0.15 : 0.12;

          return (
            <g key={node.id} transform={`translate(${pos.x}, ${pos.y})`}>
              <rect
                width={w}
                height={h}
                rx={isProcess ? 4 : 6}
                fill={color}
                opacity={bgOpacity}
                stroke={color}
                strokeWidth={isProcess ? 2 : 1.5}
                strokeDasharray={isProcess ? "4,2" : "none"}
              />

              {/* Name / title */}
              <text
                x={w / 2}
                y={isProcess ? 14 : 18}
                textAnchor="middle"
                fontSize={isProcess ? 10 : 11}
                fontWeight="600"
                fill="#1e293b"
              >
                {node.name && node.name.length > 14
                  ? node.name.slice(0, 13) + "…"
                  : node.name || "?"}
              </text>

              {/* Sub-label */}
              {node.label && (
                <text
                  x={w / 2}
                  y={isProcess ? 27 : 34}
                  textAnchor="middle"
                  fontSize={9}
                  fill={color}
                  fontWeight={500}
                >
                  {node.label}
                </text>
              )}

              {/* Additional subtext for process nodes */}
              {node.subtext && (
                <text
                  x={w / 2}
                  y={h - 4}
                  textAnchor="middle"
                  fontSize={8}
                  fill="#94a3b8"
                >
                  {node.subtext.slice(0, 20)}
                </text>
              )}

              {/* Score indicator for AI verifier */}
              {node.processType === "ai_verifier" && node.score !== undefined && (
                <circle
                  cx={w - 10}
                  cy={10}
                  r={4}
                  fill={node.score >= 0.7 ? "#059669" : node.score >= 0.4 ? "#d97706" : "#dc2626"}
                />
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
