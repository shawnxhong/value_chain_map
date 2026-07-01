import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Backend target: in Docker Compose this is the `backend` service; locally it
// defaults to the dev server on :8000.
const apiProxy = process.env.VITE_API_PROXY ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": apiProxy,
    },
  },
  build: {
    // The graph engine (cytoscape + elkjs) is ~1.9MB; it's isolated into its own chunk so the
    // initial app JS stays small (~150kB) and the engine loads in parallel.
    chunkSizeWarningLimit: 2000,
    rollupOptions: {
      output: {
        manualChunks: {
          graph: ["cytoscape", "cytoscape-elk", "elkjs"],
        },
      },
      // elkjs references the optional 'web-worker' node shim in a guarded, unreachable path
      // (cytoscape-elk calls `new ELK()` with no workerUrl, so ELK uses its inlined main-thread
      // worker). Suppress just that spurious unresolved-import warning; pass all others through.
      onwarn(warning, warn) {
        if (warning.code === "UNRESOLVED_IMPORT" && /web-worker/.test(warning.message ?? "")) {
          return;
        }
        warn(warning);
      },
    },
  },
});
