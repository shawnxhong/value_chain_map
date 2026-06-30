import { useEffect, useState } from "react";

import { apiGet } from "./api/client";
import type { Health } from "./types";

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Health>("/health")
      .then(setHealth)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem", maxWidth: 720 }}>
      <h1>Value Chain Map</h1>
      <p>Layer-2 industry structure &amp; value chain map engine — scaffold.</p>
      {error && <p style={{ color: "crimson" }}>Backend unreachable: {error}</p>}
      {health ? (
        <pre style={{ background: "#f4f1ea", padding: "1rem", borderRadius: 8 }}>
          {JSON.stringify(health, null, 2)}
        </pre>
      ) : (
        !error && <p>Checking backend…</p>
      )}
    </main>
  );
}
