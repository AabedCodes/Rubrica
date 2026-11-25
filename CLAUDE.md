# Rules for AI coding assistants in this repository

These rules apply to every coding assistant (Claude Code, Copilot, Cursor, and any other) used on Rubrica. Coding assistants are part of our attack surface (supply-chain inventory row SC-51). Changes to this file and to `.claude/` need review from the owners in `CODEOWNERS`.

## Secrets

- Never read, print, copy or write `.env`, `.env.*`, `secrets/` or any credential, token or key.
- Never put secrets in code, tests, fixtures, commit messages or logs. Test fixtures that must look like a secret contain a `CANARY-T19` marker and are fake.

## Dependencies

- Never add a dependency without first running `python scripts/admission_check.py <pypi|npm> <name>` and showing the full output. Stop and ask if the result is REVIEW or FAIL.
- Never edit `backend/uv.lock` or `frontend/package-lock.json` by hand. Use `uv add` (in `backend/`) or `npm install --save-exact` (in `frontend/`).
- Never invent package names. If you are not sure a package exists, say so; the admission check will tell you.
- Every image and Dockerfile `FROM` is pinned by `@sha256:` digest; every GitHub Action `uses:` is pinned to a full commit SHA with the version in a comment.

## Data

- Synthetic data only: no real names, emails, student IDs or course content belonging to anyone.
- Email goes to Mailpit only.

## Security tests

- Injection tests use harmless canaries in the form `CANARY-T<nn>-<4 hex>`, asking only for a marker string, a call to a logging tool, or a score change on a synthetic submission. Never write real attack payloads.

## Protected areas

- Don't change `prompts/`, `backend/mcp_server/descriptions.py`, `backend/mcp_server/tools.py`, `.github/workflows/` or `01-interfaces.md` unless the task is about them, and say so in the PR description.
- Code must match `01-interfaces.md`. If it can't, propose a change to that file instead of quietly diverging.

## Mini reports (required)

- Whenever you finish a task from `docs/plan/`, or a meaningful piece of one, write a mini report in `docs/worklog/` **in the same PR**, before saying the work is done. Copy `docs/worklog/_template.md`, name the file `YYYY-MM-DD-<task-id>-<slug>.md` (use `X` for work outside the plan), and add a line to the index in `docs/worklog/README.md`.
- Fill in every section. Record the small decisions (values chosen, alternatives rejected, things that failed), every deviation from `01-interfaces.md`, and the evidence (tests, CI runs, output). State which report sections the entry feeds.
- Say honestly that an assistant wrote part of the work, which assistant, and which parts.
- CI's `worklog` check fails a PR without an entry unless it has the `no-worklog` label. Don't add that label yourself; ask the human.

## Conventions

- Python 3.13, imports rooted at the repository (`from backend.identity import tokens`).
- Use diagram element IDs (processes 1–8, D1–D11, F1–F40, TB-1–TB-14), threat IDs (T-nn) and control IDs (Cnn) in comments, test names and commit messages.
- Run `make lint` and `make test` before proposing a change as finished.
- The PR template asks whether an assistant wrote part of the change: answer it truthfully, naming the assistant.
