// Cytoscape stylesheet for the value-chain canvas.
//
// Nodes are labeled rounded-boxes (the label IS the node, so text can never overlap text),
// colored by node_type. Edges keep the design §7.5 fact-vs-inference styling; lateral links
// (COMPETES_WITH / MIGRATES_TO) are drawn distinctly and relationship labels are revealed only
// on hover/selection to cut clutter.
//
// Typed via a single cast because several keys used here (`width:'label'`, taxi routing,
// boolean-data selectors) are not fully covered by every @types/cytoscape version.

import type { StylesheetStyle } from "cytoscape";

// node_type -> fill (white text sits on every fill). Exported so the legend stays in sync.
export const NODE_COLORS: Record<string, string> = {
  company: "#4472c4",
  value_chain_stage: "#c48a44",
  product: "#6aa84f",
  end_market: "#8e44ad",
  technology: "#16a085",
};

export const STYLESHEET = [
  {
    selector: "node",
    style: {
      shape: "round-rectangle",
      label: "data(label)",
      "text-wrap": "wrap",
      "text-max-width": "120px",
      "text-valign": "center",
      "text-halign": "center",
      color: "#fff",
      "font-size": 11,
      "font-weight": 600,
      width: "label",
      height: "label",
      padding: "9px",
      "background-color": NODE_COLORS.company,
      "border-width": 1,
      "border-color": "rgba(0,0,0,0.18)",
    },
  },
  { selector: 'node[node_type="value_chain_stage"]', style: { "background-color": NODE_COLORS.value_chain_stage } },
  { selector: 'node[node_type="product"]', style: { "background-color": NODE_COLORS.product } },
  { selector: 'node[node_type="end_market"]', style: { "background-color": NODE_COLORS.end_market } },
  { selector: 'node[node_type="technology"]', style: { "background-color": NODE_COLORS.technology } },

  // --- edges: base (flow edges use vertical "taxi" routing for a clean top-down look) ---
  {
    selector: "edge",
    style: {
      width: 2,
      "curve-style": "taxi",
      "taxi-direction": "downward",
      "taxi-turn": "40%",
      "target-arrow-shape": "triangle",
      "line-color": "#9aa0a6",
      "target-arrow-color": "#9aa0a6",
      "arrow-scale": 0.9,
      "font-size": 8,
      color: "#444",
      "text-background-color": "#ffffff",
      "text-background-opacity": 0.85,
      "text-background-padding": "2px",
    },
  },
  // layer styling (design §7.5): fact solid+opaque green; estimate neutral; inference/thesis dashed+faded
  {
    selector: 'edge[layer="fact"]',
    style: { "line-color": "#1a7f37", "target-arrow-color": "#1a7f37", opacity: 1 },
  },
  {
    selector: 'edge[layer="estimate"]',
    style: { "line-color": "#6b7280", "target-arrow-color": "#6b7280" },
  },
  {
    selector: 'edge[layer="inference"], edge[layer="thesis"]',
    style: {
      "line-style": "dashed",
      opacity: 0.55,
      "line-color": "#9aa0a6",
      "target-arrow-color": "#9aa0a6",
    },
  },

  // --- lateral (non-flow) edges override the flow look regardless of layer ---
  // COMPETES_WITH: same-level, mutual — no arrows, dotted magenta, straight.
  {
    selector: 'edge[relationship_type="COMPETES_WITH"]',
    style: {
      "curve-style": "bezier",
      "target-arrow-shape": "none",
      "line-style": "dotted",
      "line-color": "#c2557a",
      opacity: 0.8,
      width: 1.5,
    },
  },
  // MIGRATES_TO: directional tech transition, lateral — dashed teal with arrow.
  {
    selector: 'edge[relationship_type="MIGRATES_TO"]',
    style: {
      "curve-style": "bezier",
      "line-style": "dashed",
      "line-color": "#16a085",
      "target-arrow-color": "#16a085",
      opacity: 0.85,
      width: 1.5,
    },
  },

  // --- interaction states ---
  // hovering an edge reveals its relationship label + lifts it above the rest
  {
    selector: "edge.hover",
    style: { label: "data(relationship_type)", width: 3.5, opacity: 1, "z-index": 900 },
  },
  {
    selector: "edge:selected",
    style: {
      label: "data(relationship_type)",
      width: 4,
      "line-color": "#d6336c",
      "target-arrow-color": "#d6336c",
      "source-arrow-color": "#d6336c",
      opacity: 1,
      "z-index": 999,
    },
  },
  { selector: "node.hl", style: { "border-width": 3, "border-color": "#d6336c" } },
  // neighborhood-focus dimming (applied on node hover)
  { selector: ".faded", style: { opacity: 0.12, "text-opacity": 0.12 } },
] as unknown as StylesheetStyle[];
