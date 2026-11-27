# A3: SafeMarkdown and the HTML-sink lint rule

- **Author:** A (@JoudyElGayar)
- **Date finished:** 2026-11-27
- **PR / commits:** PR not opened yet; commit on branch `A/A3-safe-markdown`, stacked on `A/A1-react-shell` (PR #14)
- **Threats / controls:** T-09, T-10, C07 (browser layer)
- **Feeds report sections:** §2, §3, §4, §5
- **AI assistance:** Claude Code (desktop app, Claude Opus 5.5) wrote the component, lint rule, tests and this entry, under A's direction. A approved the plan and chose the core-ESLint rule over eslint-plugin-react.

## What was done

- `frontend/src/components/SafeMarkdown.tsx` renders model-written Markdown (feedback, chat replies, rationales) without ever creating HTML from it. This is the browser layer of C07.
- ESLint now fails on every HTML sink:
  - the `dangerouslySetInnerHTML` JSX attribute or props key;
  - `innerHTML` and `outerHTML` assignment;
  - `insertAdjacentHTML`;
  - `document.write`.
- Tests prove both: canary inputs for T-09 and T-10 against the component, and a test that runs the real ESLint config over code samples.

## How

`SafeMarkdown` wraps `react-markdown` 10.1.0 with four independent restrictions:

1. **`skipHtml`.** Raw HTML in the text is dropped, never parsed, so `<script>`, `<img onerror>` and `<iframe>` don't reach the DOM.
2. **`allowedElements` plus `unwrapDisallowed`.** Only paragraphs, emphasis, strong, code, `pre`, blockquote, lists, headings, `br`, `hr`, links and images survive. Anything else is reduced to its text.
3. **`urlTransform`.** Every URL that isn't `http:` or `https:` becomes `""` before any element sees it. This covers `javascript:`, `data:` and `vbscript:`, including mixed-case spellings, because it parses with `URL`.
4. **Element overrides:**
   - `img` becomes the text `[image removed: alt]`. No `<img>` element exists, so nothing is fetched (T-09).
   - `a` stays a link only if it's `http(s)` and its host is in the allow-list, which defaults to our own host. It then gets `rel="noopener noreferrer nofollow"` and `target="_blank"`. Otherwise it's a `<span>` with the URL as a tooltip.

The lint selectors are exported as `NO_HTML_SINKS` in `frontend/eslint.config.js`. `src/test/lintRules.test.ts` loads the real config through ESLint's Node API (in a Node test environment) and asserts each sink is an error and that safe code passes.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Core `no-restricted-syntax` selectors instead of `react/no-danger` | eslint-plugin-react on ESLint 9; `@eslint-react/eslint-plugin` | eslint-plugin-react 7.37.5 supports ESLint ≤9, and every ESLint 9 release is marked unsupported. A chose this during A1. It also covers DOM sinks that `react/no-danger` doesn't (`innerHTML`, `insertAdjacentHTML`, `document.write`) |
| Element allow-list and URL transform added on top of the plan's component | The plan's code (`skipHtml` plus `img` and `a` overrides only) | Defence in depth inside the one layer: a future Markdown plugin or parser change can't produce an element or scheme we didn't expect |
| Link allow-list defaults to our own host, with a `TODO(A6)` | A config setting for "course-approved hosts" | Nothing in `01-interfaces.md` defines where approved hosts come from. A marked TODO is better than an invented setting |
| No `remark-gfm` (tables, strikethrough) | Add it | Fewer packages; plain Markdown is enough for feedback. Can be added later after an admission check |
| Lint rule tested by running ESLint, plus a manual "sabotage" check | Trust the config | The test fails if the rule is removed (8 of 9 cases failed when it was), so a config edit or upgrade can't silently disable it |
| Canaries `CANARY-T09-4e2f`, `CANARY-T09-77c1`, `CANARY-T09-9d0e`, `CANARY-T10-a1b2`, `window.CANARY_T10` | — | Harmless markers only (CLAUDE.md); `CANARY-T09-4e2f` and `window.CANARY_T10` match the A8 test table |

## Deviations from the plan or `01-interfaces.md`

- **Plan A3 says to set `react/no-danger` to `error`.** We use core `no-restricted-syntax` selectors instead (see Decisions). The effect in CI is the same or stronger.
- **No change to `01-interfaces.md`.**

## Evidence

- **Admission check.** `react-markdown` 10.1.0: PASS (first release 2015-05-09, 98 releases, 3 maintainers, version date 2025-03-07). It adds 75 packages, almost all from the unified, remark and micromark families. `fsevents` is still the only package with an install script, and it's blocked by `ignore-scripts`. `npm audit` shows no new advisories; GHSA-g3hv-75wg-m249 is the existing A1 open item.
- **`src/components/SafeMarkdown.test.tsx`** (13 tests):
  - **T-10:**
    - an injected `<script>` doesn't run and isn't in the DOM;
    - an `<img onerror>` doesn't fire;
    - a `javascript:` link is plain text and clicking it does nothing.
  - **T-09:** inline and reference-style images create no `<img>` and the canary host never appears in the HTML; links to other sites are plain text.
  - **Other URL schemes:** `data:` and `vbscript:` links are blocked.
  - **Links that should work:** our own host stays a link with the safe `rel`, and caller-allowed hosts work.
  - **Normal output:** ordinary Markdown renders, and the output contains only allow-listed tags with no `style` or `on*` attributes.
  - **URL helpers** are unit-tested.
- **`src/test/lintRules.test.ts`** (9 tests): each of 8 sink patterns is a lint error; safe code (`textContent`, `<SafeMarkdown>`) passes. With the rule removed from the config, 8 of 9 failed (checked by hand, then the config was restored).
- **Totals.** `make lint` passes (ESLint, `tsc`, ruff). `make test`: Vitest 51 passed in 6 files; pytest 36 passed and 14 skipped by design. `make pins`: PASS.

## Open items

- **First real use.** No screen renders model text yet. A2, A5 and A6 must use `SafeMarkdown` for feedback, chat replies, rationales and appeal-agent text. A8 adds the browser-level tests: `tests/verification/test_T10_xss.py` and `test_T09_browser_image.py` with Playwright.
- **Approved hosts.** Course-approved link hosts need a source (A6, with D or C) before any off-site link can be clickable.
- **Inherited from A1:** the minimatch advisory bump, the frontend CI job (E) and the §10 body proposal.
