import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const rootDir = path.dirname(fileURLToPath(import.meta.url));
const backend = process.env.CODEX_POOL_BACKEND ?? "http://127.0.0.1:8790";

/** Dev server has no bundled /assets/* — serve from web/dist when present (cached prod HTML). */
function serveDistAssetsInDev() {
  return {
    name: "serve-dist-assets-in-dev",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = (req.url ?? "").split("?")[0];
        if (!url.startsWith("/assets/")) {
          next();
          return;
        }
        const filePath = path.join(rootDir, "dist", url);
        if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
          next();
          return;
        }
        const types = {
          ".js": "application/javascript",
          ".css": "text/css",
          ".map": "application/json",
        };
        const ext = path.extname(filePath);
        res.setHeader("Content-Type", types[ext] ?? "application/octet-stream");
        fs.createReadStream(filePath).pipe(res);
      });
    },
  };
}

const backendProxy = {
  target: backend,
  changeOrigin: true,
};

export default defineConfig({
  plugins: [vue(), serveDistAssetsInDev()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    allowedHosts: [".cpolar.cn"],
    headers: {
      "Cache-Control": "no-store",
    },
    proxy: {
      "/api": backendProxy,
      "/v1": backendProxy,
      "/healthz": backendProxy,
    },
  },
});
