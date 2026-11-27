# B1 + B2: verification framework, report generator, test-writing guide

- **Author:** B's tasks, done by E (@AabedCodes), who has taken over Person B's part
- **Date finished:** 2026-11-28
- **PR / commits:** this PR (branch `b/B1-verification-framework`)
- **Threats / controls:** all (the framework every verification test uses); C16 (pin check extended)
- **Feeds report sections:** §3 (verification evidence), Appendix A (matrix rows)
- **AI assistance:** Claude Code (Claude Opus 5.5) wrote all files, under E's direction

## What was done

- `tests/verification/framework.py`: the `@verification(...)` decorator from `01-interfaces.md` §11, with a `REGISTRY` of every decorated test. It **validates metadata at import time**:
  - threat `T-nn`, controls `Cnn`;
  - every `location` path must exist in the repo;
  - the canary's `T-nn` must match the threat, or the canary is an `input:` description;
  - `kind` and `runs` must be consistent.
- `tests/verification/plugin.py`: pytest hooks.
  - Records outcome, `observed`, `evidence`, provider/model and time for each verification test.
  - `--verification-results=PATH` writes them as JSON; `--verification-run=N` numbers repeated live runs.
  - Probabilistic tests skip automatically on `LLM_PROVIDER=fake`.
  - Fixtures: `observed`, `evidence`, `live_only`, `mailpit`, and `fake_llm`, `agent_token`, `api_client_factory`. The last three skip with the owning task's name until C1, E5 and E4 land.
- `tests/support/db.py`: the `rubrica_db` fixture.
  - Migrates a disposable PostgreSQL, seeds a two-course world for access-control tests, and downgrades at module end.
  - `as_role(role, ctx)` goes through D's real `backend.db.session()`; `raw(role)` connects with no RLS context.
- `tests/conftest.py` loads both.
- `scripts/verify_report.py`: results → `report.md`, `report.json`, `matrix_rows.csv`. Repeated runs become `k/N`. Exits 1 if any test failed; skips are listed with their reason.
- `make verify` (throwaway DB, suites, report, cleanup), `make verify-live RUNS=N`, `make test-db-up` / `test-db-down`.
- CI job `db-tests`: a PostgreSQL service container (pinned digest), runs `tests/authz` and `tests/verification`, uploads the `verification-report` artifact.
- `scripts/check_pins.py` now also checks `image:` lines inside workflows (service containers).
- `tests/verification/README.md` (B2): the template, the field rules, the 8 test rules, the fixture table, and what to do when a test finds a real gap.

## How

The decorator adds a `verification(meta=...)` marker plus a `deterministic` or `probabilistic` marker. The plugin's `pytest_runtest_makereport` wrapper keeps one record per test: the call phase, or setup when setup failed or skipped. The report reads only recorded results, so `make verify` output is exactly what ran.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Validate metadata at import time, including that `location` paths exist | free-form strings | B9 says the matrix must agree with the code; this makes a stale location a CI failure, not a spot-check finding |
| `canary` may be `input: ...` for tests that inject nothing | always require a CANARY string | tests like T-16, T-17 and T-23 feed an input, not an injection; the prefix keeps this explicit |
| Repeated live runs are separate pytest invocations (`--verification-run=i`) merged by the report | `pytest-repeat` | no new dependency (admission rule); the loop lives in `make verify-live` |
| Fixtures for unbuilt components skip with the owning task | leave them out | teammates can write tests against the agreed fixture names today |
| DB fixture is module-scoped (migrate → seed → downgrade) | one session-scoped DB | D1's tests require an empty database at module start; module scope keeps both suites independent |
| Reuse D1's `RUBRICA_D1_TEST_PORT` variable | a new variable | one database setting for every DB test |
| Generated `docs/verification/report.md` not committed yet | commit every run | it would churn on every PR; CI uploads it as an artifact; we commit the final evidence run for the report |

## Deviations from the plan or `01-interfaces.md`

- `observed` is a fixture (`observed("...")`) rather than `request.node.observed = ...`. The plugin also reads `node.observed`, so both work.
- The `seeded_db` fixture from the plan is `rubrica_db`. It seeds its own small world rather than `make seed CANARIES=1`, because the seed generator needs the Compose stack; tests that need the full seed can add a fixture once D2's generator runs without Compose.

## Evidence

- `tests/unit/test_verification_framework.py`: 14 tests (metadata validation, aggregation including `2/3` for repeated runs, report and matrix output, markdown escaping).
- `make verify` locally (Docker Desktop 29.9.3): 48 passed, 2 strict-xfail (FINDING-B4-01). `report.md` row for T-23: "1 of 4 proposed grades returned; own released=True, bob's=False, own pending=False, other course=False".
- CI `db-tests` on this PR.

## Open items

- B3 (route matrix, T-27): no FastAPI app on `main` yet.
- B5 (tokens): needs E5 and C2.
- B6 T-14 and T-32: need D6 and E6.
- B8 coverage check: needs the M1 threat register exported to `docs/threat-model/threats.csv`.
- Ask the repo admin to make `db-tests` a required check once this PR is merged.
