import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import { createApiClient, type Transport } from "./api";
import { App } from "./App";
import "./styles.css";

const MOCK_MODE = import.meta.env.MODE === "mock";

async function transport(): Promise<Transport | undefined> {
  // MOCK(E4): remove once the real identity routes are on main. In a normal
  // build MODE is "production", so this branch and the mock module are dropped
  // from the bundle, and build-guard.ts refuses `vite build --mode mock`.
  if (MOCK_MODE) {
    const { createMockTransport } = await import("./mocks/mockApi");
    return createMockTransport();
  }
  return undefined;
}

const root = document.getElementById("root");
if (!root) throw new Error("#root element missing from index.html");

transport().then((t) => {
  const api = createApiClient({ transport: t });
  createRoot(root).render(
    <StrictMode>
      <BrowserRouter>
        <App api={api} mockMode={MOCK_MODE} />
      </BrowserRouter>
    </StrictMode>,
  );
});
