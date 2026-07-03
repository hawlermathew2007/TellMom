import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://45.151.155.170:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
