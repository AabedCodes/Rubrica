// ESLint flat config for the React front end (A1).
// A3 adds the rule that bans dangerouslySetInnerHTML (C07).
import js from "@eslint/js";
import { defineConfig, globalIgnores } from "eslint/config";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

export default defineConfig([
  globalIgnores(["dist/", "node_modules/"]),
  js.configs.recommended,
  tseslint.configs.recommended,
  reactHooks.configs.flat["recommended-latest"],
  {
    files: ["**/*.{ts,tsx}"],
    rules: {
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
