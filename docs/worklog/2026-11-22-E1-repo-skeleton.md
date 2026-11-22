# E1: Repository skeleton

- **Author:** E (@AabedCodes)
- **Date finished:** 2026-11-22
- **PR / commits:** initial commit 4b4f47d on `main` (pushed directly, since an empty repository can't take a PR)
- **Threats / controls:** C14, C16; T-16, T-19 (assistant rules)
- **Feeds report sections:** §5
- **AI assistance:** Claude Code (Claude Opus 5.5) wrote all files, under E's direction

## What was done

- Folder layout from `01-interfaces.md` §1, with `__init__.py` packages under `backend/` and the plan files copied to `docs/plan/` (`01-interfaces.md` at the root).
- `Makefile` with every target from §1. Targets owned by others (`seed`, `verify`, `sbom`, `scan`) exit 1 with "not implemented (owner: X)" instead of pretending to work.
- `CODEOWNERS`, PR template (AI-assistance disclosure, admission output, "I read every AI-written line"), `.gitignore`, `.gitattributes`, `.env.example`, gitleaks pre-commit hook.
- `CLAUDE.md` and `.claude/settings.json` for coding assistants.
- `backend/pyproject.toml` with dev dependencies only (pytest, ruff), locked with `uv lock`.

## How

`backend/` is one uv project with `package = false`. Imports are rooted at the repo (`from backend.identity import tokens`): `pytest.ini` sets `pythonpath = . scripts`, and the container sets `PYTHONPATH=/app`. The ruff config lives in the root `ruff.toml` so it covers `backend/`, `scripts/` and `tests/`.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| pytest 9.2.0, ruff 0.17.4 | newest ruff 0.17.6 | 0.17.6 was 3 days old; our admission rule flags versions younger than 14 days |
| `.gitattributes`: `* text=auto eol=lf` | leave the git default | developing on Windows: a CRLF Makefile or shell script breaks inside Linux containers |
| ruff config in the root `ruff.toml` | `[tool.ruff]` in `backend/pyproject.toml` | the pyproject version silently didn't apply to `scripts/` and `tests/` (found when the formatter used a line length of 88 instead of 100) |
| Placeholder make targets exit 1 | exit 0 | a fake green is worse than a visible gap |
| CODEOWNERS: other roles' lines commented out | guess the handles | wrong handles are ignored silently; filled in when roles are claimed |

## Deviations from the plan or `01-interfaces.md`

The initial commit went straight to `main` (unavoidable for an empty repository). Every later change goes through a PR.

## Evidence

The repo builds and lints on CI from this commit onward. Admission-check output for every locked package is in PR #1.

## Open items

- Branch protection settings (approvals, required checks) are being set by the repo admin.
- CODEOWNERS handles for B, C and D, added when they claim their roles.
