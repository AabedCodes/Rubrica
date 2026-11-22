# Rubrica

Rubrica is an agent-assisted grading system for university courses, built for the AI Security capstone. Instructors publish assignments with structured rubrics; a quarantined grading agent proposes grades; the instructor approves every grade before a separate release service publishes it. Students can ask a chat agent about course material and open appeals.

The design (threats T-01 to T-37, controls C01 to C37) is in the Milestone 1 report. The shared contracts are in [`01-interfaces.md`](01-interfaces.md); the Milestone 2 task plan is in [`docs/plan/`](docs/plan/).

## Requirements

- Docker with Compose v2
- GNU `make` (on Windows: Git Bash with `make`, or WSL)
- Python 3.13 and [`uv`](https://docs.astral.sh/uv/) for running tests outside Docker

## Run it locally

```sh
make secrets   # writes random values into secrets/ (git-ignored); run once
make up        # builds and starts every service, waits until all are healthy
```

The app is at <http://127.0.0.1:8080>. Mailpit's UI (all outgoing email) is at <http://127.0.0.1:8025>. Nothing else is published.

```sh
make down      # stops the stack (keeps the database volume)
make test      # unit, authorization and deterministic verification tests
make lint      # ruff over backend, scripts and tests
```

All model calls use the scripted fake model (`LLM_PROVIDER=fake`) until the team receives provider keys.

| Target | What it does | Owner |
|---|---|---|
| `make up` / `make down` | Start / stop the Compose stack | E |
| `make secrets` | Create random Docker secrets under `secrets/` | E |
| `make seed` | Load synthetic users, courses and submissions | D |
| `make test` | Run the test suite | all |
| `make verify` | Run `tests/verification/` and write `docs/verification/report.md` | B |
| `make sbom` | Merged CycloneDX SBOM + AI-BOM | E |
| `make scan` | OSV-Scanner, pip-audit, npm audit, gitleaks, Trivy | E |

## Repository layout

See [`01-interfaces.md` §1](01-interfaces.md#1-repository-layout-owner-e). Each top-level area has an owner in [`CODEOWNERS`](CODEOWNERS).

## Contributing

- `main` is protected: every change goes through a pull request with one approving review and green CI.
- Fill in the PR template, including whether an AI assistant wrote any of the change.
- Before adding any dependency, run `python scripts/admission_check.py <pypi|npm> <package>` and paste the output into the PR. Never edit `uv.lock` or `package-lock.json` by hand.
- Synthetic data only. Injection tests use `CANARY-T<nn>-<hex>` strings, never real payloads.
- Coding assistants follow [`CLAUDE.md`](CLAUDE.md).

### Local secret scanning (optional, saves a CI round trip)

CI runs gitleaks on every push; this hook catches leaks before you commit.

```sh
pip install pre-commit   # or: uv tool install pre-commit
pre-commit install
```

The hook config is in [`.pre-commit-config.yaml`](.pre-commit-config.yaml).
