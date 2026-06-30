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
});
