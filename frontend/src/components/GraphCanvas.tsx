import cytoscape from "cytoscape";
import type { Core } from "cytoscape";
import elk from "cytoscape-elk";
import { useCallback, useEffect, useRef } from "react";

import { elkLayout, toElements } from "../graph/layout";
import { STYLESHEET } from "../graph/style";
import type { ChainGraph } from "../types";
import GraphLegend from "./GraphLegend";

// Register the ELK layered layout once. Harmless if HMR re-evaluates this module.
try {
  cytoscape.use(elk);
} catch {
  /* already registered */
}

interface Props {
  graph: ChainGraph;
  selectedEdgeId: string | null;
  onEdgeSelect: (edgeId: string | null) => void;
}

export default function GraphCanvas({ graph, selectedEdgeId, onEdgeSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  // Lay out over the flow-edge subgraph only (nodes + edges tagged `flow`), so lateral edges
  // (COMPETES_WITH / MIGRATES_TO) render but don't push competitors onto different layers.
  const runLayout = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements()
      .filter((el) => el.isNode() || Boolean(el.data("flow")))
      .layout(elkLayout())
      .run();
  }, []);

  const fit = useCallback(() => cyRef.current?.fit(undefined, 30), []);

  useEffect(() => {
    if (!containerRef.current) return;
    const cy = cytoscape({
      container: containerRef.current,
      elements: toElements(graph),
      style: STYLESHEET,
      // no constructor layout: we run our subset layout below so lateral edges are excluded
      layout: { name: "preset" },
    });
    cyRef.current = cy;
    runLayout();

    // selection -> evidence panel (unchanged wiring)
    cy.on("tap", "edge", (evt) => onEdgeSelect(evt.target.id()));
    cy.on("tap", (evt) => {
      if (evt.target === cy) onEdgeSelect(null); // click background clears selection
    });

    // neighborhood focus: dim everything but the hovered node + its immediate links
    cy.on("mouseover", "node", (evt) => {
      const node = evt.target;
      cy.elements().addClass("faded");
      node.closedNeighborhood().removeClass("faded");
      node.addClass("hl");
    });
    cy.on("mouseout", "node", () => {
      cy.elements().removeClass("faded hl");
    });
    // edge hover reveals its relationship label
    cy.on("mouseover", "edge", (evt) => evt.target.addClass("hover"));
    cy.on("mouseout", "edge", (evt) => evt.target.removeClass("hover"));

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [graph, onEdgeSelect, runLayout]);

  // reflect external selection onto the canvas
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.edges().unselect();
    if (selectedEdgeId) cy.getElementById(selectedEdgeId).select();
  }, [selectedEdgeId]);

  return (
    <div style={{ position: "relative", flex: 1, minHeight: 560 }}>
      <div
        ref={containerRef}
        style={{
          position: "absolute",
          inset: 0,
          border: "1px solid #ddd",
          borderRadius: 8,
          background: "#fcfcfb",
        }}
      />
      <AxisHint edge="top" label="▲ Upstream" />
      <AxisHint edge="bottom" label="▼ Downstream" />
      <GraphLegend onFit={fit} onRelayout={runLayout} />
    </div>
  );
}

function AxisHint({ edge, label }: { edge: "top" | "bottom"; label: string }) {
  const pos = edge === "top" ? { top: 10 } : { bottom: 10 };
  return (
    <div
      style={{
        position: "absolute",
        left: 10,
        ...pos,
        zIndex: 10,
        fontSize: 11,
        fontWeight: 600,
        color: "#9aa0a6",
        letterSpacing: 0.3,
        pointerEvents: "none",
      }}
    >
      {label}
    </div>
  );
}
