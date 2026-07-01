// Value-chain layout transform: classify edges by whether they define vertical flow, and
// produce the ELK "layered" (Sugiyama) options that render upstream suppliers at the top and
// downstream buyers / end-markets at the bottom. Pure — no Cytoscape instance needed.

import type { ElementDefinition, LayoutOptions } from "cytoscape";

import type { ChainGraph } from "../types";

// Relationships that define vertical value-chain flow: the edge's SOURCE is ranked ABOVE its
// TARGET (upstream on top). SUPPLIES_TO's source is the seller/upstream, so the natural edge
// direction already yields supplier-over-customer under a top→bottom layered layout; likewise
// SERVES_MARKET drives end-markets to the bottom, and PRODUCES puts products under their maker.
export const FLOW_RELATIONSHIPS = new Set<string>([
  "SUPPLIES_TO",
  "SERVES_MARKET",
  "PRODUCES",
  "BELONGS_TO_STAGE",
]);

// Lateral relationships: rendered, but EXCLUDED from the ranking pass so their two endpoints
// are free to sit on the same row (competitors) instead of being forced onto different layers.
export const LATERAL_RELATIONSHIPS = new Set<string>(["COMPETES_WITH", "MIGRATES_TO"]);

/** True if this relationship should drive vertical ranking (vs. render as a lateral link). */
export function isFlowEdge(relationshipType: string): boolean {
  return FLOW_RELATIONSHIPS.has(relationshipType);
}

/** Build Cytoscape elements, tagging each edge with `flow` (used for styling + rank selection). */
export function toElements(graph: ChainGraph): ElementDefinition[] {
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
      flow: isFlowEdge(e.relationship_type),
    },
  }));
  return [...nodes, ...edges];
}

// ELK layered options: top→bottom flow, generous spacing, orthogonal edge routing, and
// disconnected clusters laid out side-by-side rather than scattered. `eles` (the flow-edge
// subgraph) is attached by the caller so lateral edges don't distort the layering.
// Typed loosely because the `elk`/`nodeDimensionsIncludeLabels` keys aren't in Cytoscape's
// built-in LayoutOptions union (they come from the cytoscape-elk extension).
export function elkLayout(): LayoutOptions {
  return {
    name: "elk",
    fit: true,
    padding: 30,
    nodeDimensionsIncludeLabels: true,
    elk: {
      algorithm: "layered",
      "elk.direction": "DOWN",
      "elk.layered.spacing.nodeNodeBetweenLayers": 90,
      "elk.spacing.nodeNode": 45,
      "elk.layered.spacing.edgeNodeBetweenLayers": 30,
      "elk.separateConnectedComponents": true,
      "elk.spacing.componentComponent": 70,
      "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
      "elk.edgeRouting": "ORTHOGONAL",
    },
  } as unknown as LayoutOptions;
}
