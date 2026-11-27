// @vitest-environment node
/**
 * Proves the C07 lint rule actually fails on every HTML sink (A3), so the
 * rule can't silently stop working after a config change or an upgrade.
 * Runs the real eslint.config.js against small code samples.
 */
import { ESLint } from "eslint";
import { describe, expect, it } from "vitest";

// frontend/, without needing @types/node for fileURLToPath.
const cwd = decodeURIComponent(new URL("../..", import.meta.url).pathname);
const eslint = new ESLint({ cwd });

async function restrictedSyntaxErrors(code: string, filePath = "src/sample.tsx"): Promise<number> {
  const [result] = await eslint.lintText(code, { filePath });
  return result!.messages.filter((m) => m.ruleId === "no-restricted-syntax" && m.severity === 2).length;
}

describe("lint rule: no HTML sinks (C07, T-10)", () => {
  it.each([
    ["JSX dangerouslySetInnerHTML", "export const A = (p: { t: string }) => <div dangerouslySetInnerHTML={{ __html: p.t }} />;"],
    ["props object", "export const props = { dangerouslySetInnerHTML: { __html: 'x' } };"],
    ["quoted props key", "export const props = { 'dangerouslySetInnerHTML': { __html: 'x' } };"],
    ["innerHTML assignment", "export function f(el: HTMLElement, t: string) { el.innerHTML = t; }"],
    ["computed innerHTML assignment", "export function f(el: HTMLElement, t: string) { el['innerHTML'] = t; }"],
    ["outerHTML assignment", "export function f(el: HTMLElement, t: string) { el.outerHTML = t; }"],
    ["insertAdjacentHTML", "export function f(el: HTMLElement, t: string) { el.insertAdjacentHTML('beforeend', t); }"],
    ["document.write", "export function f(t: string) { document.write(t); }"],
  ])("fails on %s", async (_name, code) => {
    expect(await restrictedSyntaxErrors(code)).toBeGreaterThan(0);
  });

  it("passes on safe code: text content and SafeMarkdown", async () => {
    const code = [
      "import { SafeMarkdown } from './components/SafeMarkdown';",
      "export function f(el: HTMLElement, t: string) { el.textContent = t; }",
      "export const A = (p: { t: string }) => <SafeMarkdown text={p.t} />;",
    ].join("\n");
    expect(await restrictedSyntaxErrors(code)).toBe(0);
  });
});
