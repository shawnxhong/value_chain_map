// Shared API types, mirroring the backend Pydantic contracts (plan/01-data-model.md).

export interface Health {
  status: string;
  version: string;
  extract_model: string;
  verify_model: string;
}

// --- graph (GET /api/graph/chain/{chain}) --------------------------------- //

export interface GraphNode {
  id: string;
  node_type: string;
  canonical_name: string;
  chain: string | null;
}

export interface GraphEdge {
  id: string;
  source: string; // source_node_id
  target: string; // target_node_id
  relationship_type: string;
  layer: "fact" | "estimate" | "inference" | "thesis";
  confidence_label: "high" | "medium" | "low";
  confidence_reason: string;
  status: "candidate" | "confirmed" | "deprecated" | "rejected";
  payer_node_id: string | null;
  receiver_node_id: string | null;
  payment_type: string | null;
  as_of_date: string; // ISO date
  concentration_pct: string | null;
}

export interface ChainGraph {
  chain: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// --- evidence (GET /api/evidence/{edge_id}) ------------------------------- //

export interface EvidenceItem {
  id: string;
  source_type: string;
  title: string;
  publisher: string | null;
  published_at: string | null;
  retrieved_at: string | null;
  url: string | null;
  accession_number: string | null;
  page: number | null;
  section: string | null;
  excerpt: string;
  excerpt_hash: string;
  extraction_method: string;
}

export interface EdgeEvidence {
  edge_id: string;
  evidence: EvidenceItem[];
}
