import { useCallback, useEffect, useMemo, useState } from "react";

import { apiGet } from "./api/client";
import EdgeDetailPanel from "./components/EdgeDetailPanel";
import GraphCanvas from "./components/GraphCanvas";
import type { ChainGraph } from "./types";

export default function App() {
  const [chainInput, setChainInput] = useState("hbm");
  const [chain, setChain] = useState("hbm");
  const [graph, setGraph] = useState<ChainGraph | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [reloadKey, setReloadKey] = useState(0); // bump to re-fetch after a review action

  useEffect(() => {
    setLoading(true);
    setError(null);
    apiGet<ChainGraph>(`/graph/chain/${encodeURIComponent(chain)}`)
      .then(setGraph)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [chain, reloadKey]);

  const nodeName = useCallback(
    (id: string) => graph?.nodes.find((n) => n.id === id)?.canonical_name ?? id,
    [graph],
  );
  const selectedEdge = useMemo(
    () => graph?.edges.find((e) => e.id === selectedEdgeId) ?? null,
    [graph, selectedEdgeId],
  );

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "1.5rem", maxWidth: 1200 }}>
      <h1 style={{ marginBottom: 4 }}>Value Chain Map</h1>
      <p style={{ marginTop: 0, color: "#666" }}>
        Layer-2 industry structure &amp; value chain — click an edge to read its evidence.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setSelectedEdgeId(null);
          setChain(chainInput.trim());
        }}
        style={{ display: "flex", gap: 8, margin: "12px 0" }}
      >
        <input
          value={chainInput}
          onChange={(e) => setChainInput(e.target.value)}
          placeholder="chain (e.g. hbm)"
          style={{ padding: "6px 8px", fontSize: 14 }}
        />
        <button type="submit" style={{ padding: "6px 14px" }}>
          Load
        </button>
        {loading && <span style={{ alignSelf: "center", color: "#666" }}>Loading…</span>}
      </form>

      {error && <p style={{ color: "crimson" }}>Could not load graph: {error}</p>}
      {graph && graph.edges.length === 0 && !loading && (
        <p style={{ color: "#666" }}>
          No edges for chain “{graph.chain}”. Ingest a document and run the pipeline, then load again.
        </p>
      )}

      {graph && (
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
          <GraphCanvas
            graph={graph}
            selectedEdgeId={selectedEdgeId}
            onEdgeSelect={setSelectedEdgeId}
          />
          {selectedEdge ? (
            <EdgeDetailPanel
              edge={selectedEdge}
              nodeName={nodeName}
              onReviewed={() => setReloadKey((k) => k + 1)}
            />
          ) : (
            <aside
              style={{
                width: 360,
                padding: "12px 16px",
                border: "1px dashed #ddd",
                borderRadius: 8,
                color: "#888",
              }}
            >
              Select an edge to see its layer, confidence, and source excerpts.
            </aside>
          )}
        </div>
      )}
    </main>
  );
}
