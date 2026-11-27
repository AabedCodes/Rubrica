/**
 * Playwright for the front end (A8 prep).
 *
 * e2e/ holds browser tests that run against the MOCKED front end (`npm run
 * dev:mock`): the T-09 and T-10 checks on model-written text. The full
 * main-workflow test (tests/e2e/test_main_workflow.spec.ts, plan A8) and the
 * verification-suite versions (tests/verification/test_T09_*.py, test_T10_*.py,
 * B's framework) need the real stack and come later.
 *
 * Browsers are not downloaded by `npm install` (install scripts are off, C14).
 * Run `npx playwright install chromium` once, or use an installed Chrome by
 * setting channel: "chrome" below.
 */
import { defineConfig, devices } from "@playwright/test";

const PORT = 5173;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: "off",
  },
  webServer: {
    command: "npm run dev:mock",
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: true,
    timeout: 60_000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
