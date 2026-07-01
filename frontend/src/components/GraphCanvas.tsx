import cytoscape from "cytoscape";
import type { Core, ElementDefinition, StylesheetStyle } from "cytoscape";
import { useEffect, useRef } from "react";

import type { ChainGraph } from "../types";

// fact edges are solid + opaque; inference/thesis are dashed + faded so unverified
// relationships read as obviously weaker (design §7.5).
const STYLESHEET: StylesheetStyle[] = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "font-size": 10,
      "background-color": "#4472c4",
      color: "#222",
      "text-valign": "bottom",
      "text-halign": "center",
      width: 22,
      height: 22,
    },
  },
  {
    selector: 'node[node_type="value_chain_stage"]',
    style: { "background-color": "#c48a44", shape: "round-rectangle" },
  },
  {
    selector: 'node[node_type="product"]',
    style: { "background-color": "#6aa84f" },
  },
  {
    selector: "edge",
    style: {
      label: "data(relationship_type)",
      "font-size": 7,
      color: "#666",
      width: 2,
      "curve-style": "bezier",
      "target-arrow-shape": "triangle",
      "line-color": "#9aa0a6",
      "target-arrow-color": "#9aa0a6",
    },
  },
  {
    selector: 'edge[layer="fact"]',
    style: { "line-color": "#1a7f37", "target-arrow-color": "#1a7f37" },
  },
  {
    selector: 'edge[layer="inference"], edge[layer="thesis"]',
    style: { "line-style": "dashed", opacity: 0.5 },
  },
  {
    selector: "edge:selected",
    style: { width: 4, "line-color": "#d6336c", "target-arrow-color": "#d6336c", opacity: 1 },
  },
];

function toElements(graph: ChainGraph): ElementDefinition[] {
  const nodes: ElementDefinition[] = graph.nodes.map((n) => ({
    data: { id: n.id, label: n.canonical_name, node_type: n.node_type },
  }));
  const edges: ElementDefinition[] = graph.edges.map((e) => ({
    data: {
      id: e.id,
      source: e.source,
      target: e.target,
      relationship_type: e.relationship_type,
      layer: e.layer,
    },
  }));
  return [...nodes, ...edges];
}

interface Props {
  graph: ChainGraph;
  selectedEdgeId: string | null;
  onEdgeSelect: (edgeId: string | null) => void;
}

export default function GraphCanvas({ graph, selectedEdgeId, onEdgeSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const cy = cytoscape({
      container: containerRef.current,
      elements: toElements(graph),
      style: STYLESHEET,
      layout: { name: "cose", animate: false, padding: 20 },
    });
    cyRef.current = cy;

    cy.on("tap", "edge", (evt) => onEdgeSelect(evt.target.id()));
    cy.on("tap", (evt) => {
      if (evt.target === cy) onEdgeSelect(null); // click background clears selection
    });

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [graph, onEdgeSelect]);

  // reflect external selection onto the canvas
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.edges().unselect();
    if (selectedEdgeId) cy.getElementById(selectedEdgeId).select();
  }, [selectedEdgeId]);

  return (
    <div
      ref={containerRef}
      style={{ flex: 1, minHeight: 560, border: "1px solid #ddd", borderRadius: 8 }}
    />
  );
}
