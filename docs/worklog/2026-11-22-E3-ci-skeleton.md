# E3: CI skeleton and pin checker

- **Author:** E (@AabedCodes)
- **Date finished:** 2026-11-22
- **PR / commits:** #1 (c99cc71)
- **Threats / controls:** T-17 · C16
- **Feeds report sections:** §5.2, §3 (T-17 evidence)
- **AI assistance:** Claude Code (Claude Opus 5.5) wrote all files, under E's direction

## What was done

- `.github/workflows/ci.yml` with four jobs:
  - `lint`: ruff check and format;
  - `test`: pytest;
  - `pins`;
  - `compose-smoke`: `make secrets`, `make up`, `egress_smoke.sh`, logs, `down -v`.
- `scripts/check_pins.py` fails when:
  - an action isn't pinned to a 40-hex SHA;
  - an `image:` has no digest;
  - a `FROM` or `COPY --from=<image>` has no digest;
  - a lockfile is missing.
- `tests/unit/test_check_pins.py`, including the T-17 canary inputs (`actions/checkout@v4`, `postgres:18`).

## How

`check_pins.py` is line-based and uses only the standard library, so it runs before anything is installed. It understands build-stage aliases, so `FROM base AS final` and `COPY --from=uv` aren't flagged. `test_this_repository_is_pinned` runs it against the repo itself, so any unpinned addition fails CI.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Actions pinned: checkout v7.0.1, setup-uv v10.4.0 (SHAs looked up from the tags) | tags | C16; the T-17 threat |
| Top-level `permissions: contents: read`, `persist-credentials: false`, never `pull_request_target` | defaults | least-privilege token; no repo write access from PR code |
| A short SHA counts as unpinned | accept 7+ hex | short SHAs can collide; GitHub only guarantees full SHAs |
| `compose-smoke` added to the skeleton | wait for E8 | it was the only way to test E2 without local Docker, and it found a real bug on its first run |

## Deviations from the plan or `01-interfaces.md`

`compose-smoke` isn't in the E8 job table. It was added early, and E8 keeps it.

## Evidence

The four jobs are green on PR #1. 18 unit tests pass, 1 network test is skipped by default (`RUBRICA_NETWORK_TESTS=1` enables it).

## Open items

- E8 adds the `deps`, `secrets`, `models`, `admission`, `images` and `sbom` jobs.
- The repo admin makes the four jobs required checks on `main`.
