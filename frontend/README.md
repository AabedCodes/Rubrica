# Rubrica front end

React + Vite + TypeScript single-page app (owner: A). Served in production by the `web` service, which `deploy/backend.Dockerfile` builds with `npm ci --ignore-scripts`.

## Run it

```bash
nvm use            # Node 22, from .nvmrc
npm ci             # install scripts are off (.npmrc)
npm run dev:mock   # http://127.0.0.1:5173 with the mock API, no backend needed
npm run dev        # http://127.0.0.1:5173, /api proxied to the stack on 127.0.0.1:8080
```

`npm run lint`, `npm run typecheck`, `npm test` and `npm run build` are also run by `make lint` and `make test` once `npm ci` has been run here. `npx vite preview` serves the production build with the exact security headers from `01-interfaces.md` §10, which is how to check for CSP violations.

## Mock API

Until the backend routes exist, `src/mocks/mockApi.ts` answers them in memory. It is loaded only in mock mode, and `build-guard.ts` refuses to build a production bundle in mock mode. Every mocked route is tagged with the task that will replace it:

```bash
grep -rn "MOCK(" src
```

Synthetic sign-ins for mock mode (fake values; the password carries the `CANARY-T19` marker):

| Email | Password | TOTP code |
|---|---|---|
| `student1@example.test` | `mock-only-CANARY-T19` | none |
| `instructor1@example.test` | `mock-only-CANARY-T19` | `123456` |

Request and response shapes that `01-interfaces.md` §10 doesn't define yet are in `src/apiTypes.ts`, each marked `ASSUMED`.

## Rules

- New packages: run `python scripts/admission_check.py npm <name> <version>` first and paste the output in the PR. Install with `npm install --save-exact`; never edit `package-lock.json` by hand.
- No inline scripts or styles (the CSP blocks them): styling goes in `.css` files.
- Never use `localStorage` or `sessionStorage` (ESLint fails the build).
- All requests go through `src/api.ts`.
