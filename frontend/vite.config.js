import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Les fichiers compilés vont sous /static/ (et non /assets/) pour éviter la
  // collision avec le montage statique /assets du backend (images des PDF pour
  // Remotion), proxifié par nginx vers le backend en production.
  build: {
    assetsDir: "static",
  },
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
