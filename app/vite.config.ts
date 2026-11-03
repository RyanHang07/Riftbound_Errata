// The local app (slice 17). `npm run dev` proxies /api to the Python API on
// 8765 (`make app-api`); `make app` serves the built files from the API itself.
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { host: "127.0.0.1", port: 5173, proxy: { "/api": "http://127.0.0.1:8765" } },
});
