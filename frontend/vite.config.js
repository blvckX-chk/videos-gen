import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy des appels /api vers le backend FastAPI pour éviter les soucis CORS en dev.
    proxy: {
      "/api": "http://localhost:8000",
      "/renders": "http://localhost:8000",
      "/assets": "http://localhost:8000",
      "/audio": "http://localhost:8000",
      "/audio_sources": "http://localhost:8000",
      "/design": "http://localhost:8000",
    },
  },
});
