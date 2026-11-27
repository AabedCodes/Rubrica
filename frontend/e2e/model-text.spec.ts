/**
 * Browser checks for C07 on the mocked front end (A8 prep; plan A8 test table).
 *
 * T-09: model-written Markdown carrying an image canary must not make the
 *       browser fetch anything (no <img>, no request to the canary host).
 * T-10: model-written text carrying <script>, an onerror handler and a
 *       javascript: link must not run anything: window.CANARY_T10 stays undefined.
 *
 * The mock seeds these canaries into Student Two's released feedback (and the
 * chat agent's T-09 fixture reply). The mock lives in the page, so every test
 * navigates with clicks after one page load: a reload would reset it.
 */
import { expect, test, type Page } from "@playwright/test";

const COURSE = "00000000-0000-4000-8000-0000000000c1";
const PASSWORD = "mock-only-CANARY-T19"; // fake mock-only value, see frontend/README.md

async function signInAndOpen(page: Page, email: string, path: string) {
  await page.goto(path); // redirected to the login page, then back here
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
}

function recordRequests(page: Page): string[] {
  const urls: string[] = [];
  page.on("request", (r) => urls.push(r.url()));
  return urls;
}

test("T-09: an image in model-written feedback is shown as text and never requested", async ({ page }) => {
  const requests = recordRequests(page);
  await signInAndOpen(page, "student2@example.test", `/courses/${COURSE}/grades`);
  await expect(page.getByRole("heading", { name: /^Grade: .* \/ 8$/ })).toBeVisible();

  await expect(page.getByText("[image removed: x]")).toBeVisible();
  await expect(page.locator('img[src*="canary.example"]')).toHaveCount(0);
  await expect(page.locator("main img")).toHaveCount(0);
  expect(requests.filter((u) => u.includes("canary.example"))).toEqual([]);
});

test("T-10: script, onerror and javascript: links in model text never run", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await signInAndOpen(page, "student2@example.test", `/courses/${COURSE}/grades`);
  await expect(page.getByRole("heading", { name: /^Grade: .* \/ 8$/ })).toBeVisible();

  // The link is plain text, not an anchor; clicking it does nothing.
  const link = page.locator(".link-removed", { hasText: "click" });
  await expect(link).toBeVisible();
  await expect(page.locator('a[href^="javascript:"]')).toHaveCount(0);
  await link.click();

  await expect(page.locator("main script")).toHaveCount(0);
  await expect(page.locator("[onerror]")).toHaveCount(0);
  expect(await page.evaluate(() => (window as unknown as { CANARY_T10?: number }).CANARY_T10)).toBeUndefined();
  expect(await page.content()).not.toContain("window.CANARY_T10=1</script>");
  expect(errors).toEqual([]);
});

test("T-09: the chat agent's image fixture is not fetched either", async ({ page }) => {
  const requests = recordRequests(page);
  await signInAndOpen(page, "student1@example.test", `/courses/${COURSE}/chat`);
  await page.getByLabel("Your question").fill("Explain trust boundaries with a diagram");
  await page.getByRole("button", { name: "Ask" }).click();

  await expect(page.getByText("[image removed: fixture]")).toBeVisible();
  expect(requests.filter((u) => u.includes("rubrica-canaries"))).toEqual([]);
});
