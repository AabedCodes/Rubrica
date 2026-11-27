import react from "@vitejs/plugin-react";
import { configDefaults, defineConfig } from "vitest/config";
import { assertNoMockInBuild } from "./build-guard.ts";

// The `web` service (process 1) publishes 127.0.0.1:8080 and serves /api.
const BACKEND = "http://127.0.0.1:8080";

// Security headers from 01-interfaces.md §10, copied verbatim. `vite preview`
// serves the production build with them so CSP violations show up locally
// (A1 step 6). Not applied to the dev server: React's hot reload needs an
// inline script there. The `web` service sets the real headers (A, E).
export const SECURITY_HEADERS = {
  "Content-Security-Policy":
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
};

export default defineConfig(({ command, mode }) => {
  assertNoMockInBuild(command, mode);
  const mock = mode === "mock";
  return {
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      port: 5173,
      strictPort: true,
      // In mock mode nothing leaves the browser; otherwise /api goes to the
      // local stack so the session cookie stays same-origin.
      proxy: mock ? undefined : { "/api": { target: BACKEND, changeOrigin: false } },
    },
    preview: {
      host: "127.0.0.1",
      port: 4173,
      strictPort: true,
      headers: SECURITY_HEADERS,
    },
    build: {
      sourcemap: false,
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      // e2e/ holds Playwright browser tests, run with `npm run e2e`, not Vitest.
      exclude: [...configDefaults.exclude, "e2e/**"],
      restoreMocks: true,
    },
  };
});
