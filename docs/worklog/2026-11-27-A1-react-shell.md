# A1: React shell and npm supply-chain hardening

- **Author:** A (@JoudyElGayar)
- **Date finished:** 2026-11-27
- **PR / commits:** PR not opened yet; commit on branch `A/A1-react-shell`
- **Threats / controls:** T-10, T-16, T-19 (mock canary), C14, C27, C28, C29 (UI side only)
- **Feeds report sections:** §2, §4, §5, §9
- **AI assistance:** Claude Code (desktop app, Claude Opus 5.5) wrote the code, tests, config and this entry, under A's direction. A chose between the options at each decision below and reviewed the result.

## What was done

- `frontend/` now holds a React 19 + Vite 8 + TypeScript 6 single-page app: routing, a login page, a TOTP page for instructors (C27), navigation by role, a course switcher, and placeholder pages for the screens A2–A7 will build.
- `src/api.ts` is the one HTTP client. It sends same-origin cookies and adds `X-CSRF-Token` to POST, PUT and DELETE. On `401 reauth_required` it opens a re-auth modal (C28) and retries exactly once. It never uses Web Storage.
- npm hardening: `.npmrc` (`ignore-scripts`, `save-exact`, `engine-strict`), `.nvmrc` = 22, exact versions, committed `package-lock.json`. Every package went through the admission check.
- A mock API (`src/mocks/`) stands in for E4. Each route is tagged `MOCK(E4)`, it is loaded only in mock mode, and a build guard refuses to bundle it.
- `make lint` and `make test` now also run ESLint, `tsc` and Vitest for the front end once `npm ci` has been run in `frontend/`. Members without Node see a "skipped" line instead.

## How

- **Entry and routing.** `main.tsx` builds the API client and renders `<App>` inside a `BrowserRouter`. `App.tsx` defines the routes. `navigation.ts` lists each course screen with the roles allowed to see it, and both the side menu and the route guard read that one list, so they can't disagree. The guards are a convenience only: the API enforces roles and course membership (C29).
- **Session and auth state.** `auth/AuthContext.tsx` loads `GET /me` on start, handles login and TOTP, and resets the CSRF token whenever the session changes. `auth/ReauthProvider.tsx` registers the re-auth handler with the client and shows the modal. If several requests need re-auth at the same time, the user is asked only once.
- **Mock mode.** `npm run dev:mock` runs Vite with `--mode mock`. In a production build `import.meta.env.MODE` is `"production"`, so the dynamic import of the mock is dropped from the bundle. `build-guard.ts` makes `vite build --mode mock` fail.
- **Response shapes.** `01-interfaces.md` §10 names the routes but not their bodies. The shapes we need are all in `src/apiTypes.ts`, each marked `ASSUMED`.
- **CSP.** `vite preview` serves the production build with the §10 security headers copied verbatim (`SECURITY_HEADERS` in `vite.config.ts`), so CSP problems show up locally. No inline scripts or styles anywhere, and no `style=` attributes.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Wrote the Vite scaffold by hand | `npm create vite@<pinned>` (the plan's step 1) | `create-vite` is one more package executed on the developer machine; the scaffold is six small files |
| Each package pinned to the newest stable version at least 14 days old, checked with `admission_check.py npm <name> <version>` | Latest versions (several were 0–3 days old) | The check only applies its 14-day new-version rule when a version is given. Without one it passed releases published that day |
| TypeScript 6.0.3, not 7.0.2 | TypeScript 7 | typescript-eslint 8.72.2 supports TypeScript up to <6.1 |
| ESLint 10.14.0 without eslint-plugin-react | ESLint 9 + eslint-plugin-react (as the plan says); `@eslint-react/eslint-plugin` | eslint-plugin-react 7.37.5 supports ESLint up to 9 only, and every ESLint 9 release is marked unsupported. A chose to block `dangerouslySetInnerHTML` with core `no-restricted-syntax` in A3 instead |
| Mock as an in-memory transport behind the client's `fetch`-shaped interface | MSW (Mock Service Worker) | No extra dependency; the same transport is reused by the tests |
| Web Storage banned with ESLint `no-restricted-globals` and `no-restricted-properties` | Code review only | The plan requires no tokens in `localStorage`; a lint rule makes CI enforce it |
| Upgraded the local npm to 11.21.2 (nvm Node 22 only; admission check PASS) | `--legacy-peer-deps`; dropping Vitest | npm 10.9.9, bundled with Node 22, crashes (`Cannot read properties of null (reading 'edgesOut')` in arborist `#loadPeerSet`) resolving Vitest 5's optional peers. The lockfile stays at v3, so `npm ci` in the Docker build is unaffected |
| `redirect: "error"` and relative-path-only requests in `api.ts` | Default fetch behaviour | The client should only ever talk to our own `/api` |
| Post-login redirect only to same-site paths (`safeNext`) | Trust `location.state.from` | Prevents an open redirect through the login page |

## Deviations from the plan or `01-interfaces.md`

- **Plan A1 step 1:** hand-written scaffold instead of `npm create vite` (see Decisions).
- **Plan A3 (decided now, implemented in A3):** core ESLint `no-restricted-syntax` instead of `react/no-danger` from eslint-plugin-react.
- **`01-interfaces.md` §10 does not define request or response bodies.** The shell assumes the shapes in `frontend/src/apiTypes.ts`:
  - `GET /api/auth/csrf` returns `{csrf_token}`.
  - Login returns `{status: "ok" | "totp_required"}`.
  - `GET /me` returns `{id, display_name, role}`.
  - `GET /courses` returns a list of `{id, code, title, role}`.
  - Errors are `{error: "<fixed code>"}`.

  `01-interfaces.md` was **not** changed in this PR. A proposal PR to §10 for E (the section owner) is an open item.
- **Plan A1 step 6:** the `web` service still runs the placeholder, so serving the build from `web` couldn't be tested. The CSP was checked with `vite preview` instead.

## Evidence

- **Admission checks.** All 17 packages PASS at the pinned versions: react 19.3.1, react-dom 19.3.1, react-router 8.5.1, vite 8.3.8, @vitejs/plugin-react 6.3.0, typescript 6.0.3, @types/react 19.3.0, @types/react-dom 19.3.0, eslint 10.14.0, @eslint/js 10.0.1, typescript-eslint 8.72.2, eslint-plugin-react-hooks 7.1.1, vitest 5.1.0, jsdom 31.0.0, @testing-library/react 16.3.3, @testing-library/dom 10.4.2, @testing-library/user-event 14.6.10. Full output goes in the PR description.
  - The first run on this Mac gave REVIEW for every package with "could not reach the registry". The python.org build of Python 3.13 has no CA bundle (`CERTIFICATE_VERIFY_FAILED`). Re-running with `SSL_CERT_FILE=/etc/ssl/cert.pem` (verification still on) fixed it. Worth knowing for anyone on macOS.
- **Install scripts.** `fsevents` is the only package in the lockfile with an install script, and `ignore-scripts` blocked it.
- **Vitest.** 29 tests in 4 files pass:
  - `src/api.test.ts`: CSRF on writes only; one CSRF fetch, then reuse; reset on session change; drop after 403; re-auth then exactly one retry; no second retry; no retry on cancel; one prompt for concurrent requests; opt-out for login and re-auth; non-JSON errors; absolute URLs refused; Web Storage never touched.
  - `src/App.test.tsx`: redirect to login; student sign-in returns to the requested page with student navigation only; student gets "Not available" on an instructor screen; instructor goes through TOTP; wrong-password message; course switcher; sign out; re-auth modal and retry end to end; `safeNext`.
  - `src/mocks/mockApi.test.ts` and `build-guard.test.ts`.
- **`make lint`:** ESLint, `tsc` and ruff all pass. **`make test`:** Vitest 29 passed; pytest 36 passed, 14 skipped (D's database tests and the network test are skipped by design). **`make pins`:** PASS.
- **Production build.** `npm run build` gives `index.html` with no inline script or style, one JS file and one CSS file.
  - `grep` finds no mock code in `dist/`: no `CANARY-T19`, `mock-csrf`, `createMockTransport` or mock emails.
  - `vite build --mode mock` fails with "Refusing to build in mock mode".
- **Browser check.** Under `vite preview` with the §10 headers, the login page renders with its stylesheet and the console shows no CSP violations. The only error is `GET /api/me → 404` from the placeholder backend, which the app treats as signed out. Response headers confirmed: the CSP exactly as in §10, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`. `localStorage` and `sessionStorage` are empty.

## Open items

- **minimatch advisory, accepted for now.** `npm audit` reports GHSA-g3hv-75wg-m249 (moderate: minimatch <11.0.1 denial of service via globparts amplification) through eslint 10.14.0 and typescript-eslint 8.72.2. It affects lint tooling only and never reaches the built app.
  - The fixed versions were too new for our 14-day rule: eslint 10.15.0 (REVIEW, 13 days) and typescript-eslint 8.73.0 (11 days).
  - A accepted it. Plan: bump both once they are 14 days old (around 28 and 30 Nov) and re-run `npm audit`. That gives report §4 a before-and-after finding.
  - `docs/remediation-log.md` is only in open PR #8, so the remediation-log line waits for that PR to merge.
- **No frontend job in CI.** `.github/workflows/` is E's protected area. Ask E for an `npm ci && npm run lint && npm run typecheck && npm test && npm run build` job on Node 22.
- **§10 proposal for E.** Propose the request and response bodies in `src/apiTypes.ts` as an addition to `01-interfaces.md` §10 (tag E). Switch the `MOCK(E4)` routes to the real ones when E4 merges.
- **`web` must serve the build.** Once `web` stops running the placeholder, it has to serve `/app/frontend_dist` with the §10 headers and fall back to `index.html` for client-side routes. Check this with E.
- **Local machine setup.** Teammates on macOS with python.org Python need `SSL_CERT_FILE=/etc/ssl/cert.pem` (or "Install Certificates.command") for the admission check. On this machine `~/.zshrc` doesn't load nvm or put `~/Library/Python/3.13/bin` (uv) on PATH yet.
