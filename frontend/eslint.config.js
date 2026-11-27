// ESLint flat config for the React front end (A1, A3).
import js from "@eslint/js";
import { defineConfig, globalIgnores } from "eslint/config";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

// C07, T-09, T-10: no code path may turn a string into HTML. Model-written
// text goes through <SafeMarkdown> or is shown as plain text.
// The plan names `react/no-danger` from eslint-plugin-react, but that plugin
// only supports ESLint up to 9, which is end-of-life; these core selectors
// cover the same attribute and the DOM sinks besides (worklog A3).
const HTML_SINKS = "Model-written text must go through <SafeMarkdown> or be shown as plain text (C07, T-10).";
export const NO_HTML_SINKS = [
  { selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']", message: `dangerouslySetInnerHTML is banned. ${HTML_SINKS}` },
  { selector: "Property[key.name='dangerouslySetInnerHTML']", message: `dangerouslySetInnerHTML is banned. ${HTML_SINKS}` },
  { selector: "Property[key.value='dangerouslySetInnerHTML']", message: `dangerouslySetInnerHTML is banned. ${HTML_SINKS}` },
  { selector: "AssignmentExpression > MemberExpression.left[property.name=/^(innerHTML|outerHTML)$/]", message: `innerHTML/outerHTML assignment is banned. ${HTML_SINKS}` },
  { selector: "AssignmentExpression > MemberExpression.left[property.value=/^(innerHTML|outerHTML)$/]", message: `innerHTML/outerHTML assignment is banned. ${HTML_SINKS}` },
  { selector: "CallExpression[callee.property.name='insertAdjacentHTML']", message: `insertAdjacentHTML is banned. ${HTML_SINKS}` },
  { selector: "CallExpression[callee.object.name='document'][callee.property.name=/^(write|writeln)$/]", message: `document.write is banned. ${HTML_SINKS}` },
];

export default defineConfig([
  globalIgnores(["dist/", "node_modules/"]),
  js.configs.recommended,
  tseslint.configs.recommended,
  reactHooks.configs.flat["recommended-latest"],
  {
    files: ["**/*.{ts,tsx}"],
    rules: {
      "no-restricted-syntax": ["error", ...NO_HTML_SINKS],
      // Session state never goes to Web Storage, where any injected script
      // could read it (A1 step 4; T-10). The session is an HttpOnly cookie and
      // the CSRF token lives in memory only.
      "no-restricted-globals": [
        "error",
        { name: "localStorage", message: "Never use Web Storage: session state stays in memory (A1, T-10)." },
        { name: "sessionStorage", message: "Never use Web Storage: session state stays in memory (A1, T-10)." },
      ],
      "no-restricted-properties": [
        "error",
        { object: "window", property: "localStorage", message: "Never use Web Storage (A1, T-10)." },
        { object: "window", property: "sessionStorage", message: "Never use Web Storage (A1, T-10)." },
      ],
    },
  },
]);
