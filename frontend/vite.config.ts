import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  // Production serves the dashboard under /app/ (deploy/web.Dockerfile).
  base: process.env.VITE_BASE ?? "/",
  plugins: [react()],
  server: {
    port: 5173,
  },
});
