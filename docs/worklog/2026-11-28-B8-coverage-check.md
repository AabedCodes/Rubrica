# B8: coverage check, threat register export, and E's first verification tests

- **Author:** B's task (done by E, @AabedCodes) plus E13 tests
- **Date finished:** 2026-11-28
- **PR / commits:** this PR (stacked on #27, the verification framework)
- **Threats / controls:** T-16, T-17, T-19 · C12, C14, C16, C31
- **Feeds report sections:** §3, Appendix A
- **AI assistance:** Claude Code (Claude Opus 5.5) wrote all files, under E's direction

## What was done

- `scripts/export_threats.py` parses the M1 report's Section 5 register into `docs/threat-model/threats.csv`: 37 threats (7 Critical, 22 High, 8 Medium; 6 on the optional features). The counts match M1 §6.
- `scripts/check_coverage.py` fails when:
  - a Critical or High threat has no verification test (with `--results`, no *passing* test);
  - a test names a threat that isn't in the register, or a control outside C01–C37.

  It reads the owner of each missing test from the plan files and prints it by name. It reports gaps but exits 0 until **Fri 4 Dec**, then starts failing (`--enforce-from`). Metadata errors always fail.
- It runs in CI (`db-tests`) against the real results and uploads `coverage.md` with the verification report.
- New verification tests (E13):
  - **T-16:** an invented package name gets FAIL, and the typo `reqeusts` gets a "did you mean: requests?" suggestion.
  - **T-17:** a tag-pinned action, an undigested service image and an undigested `FROM` are all reported, with exit 1; the real repo passes.
  - **T-19, database half:** the `rubrica_ingest` credential gets 42501 on `submissions`, `proposed_grades`, `answer_keys` and `users`, and can't delete audit rows.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Valid controls are C01–C37 | parse controls from M1 | M1 has no control table; C31–C37 are defined in the M2 plan README |
| Match results to the registry on threat + function name | full test ID | pytest imports test modules by basename, the script by package path |
| Report-only until the freeze, then enforced | enforce now | enforcing now would block every PR for three days while owners write tests |
| T-19's gitleaks half deferred to E8's `secrets` job | add gitleaks now | needs the gitleaks binary in CI; the database half shows the blast radius today |
| Kept T-29 required | drop it, since M1 avoids T-29 by design | it's High in the register; D's test should show scans are rejected |

## Evidence

`make verify` locally: 51 passed, 2 xfailed. The report shows T-16, T-17, T-19 and T-23 passed. `check_coverage`: **4 of 29** Critical and High threats covered.

## Open items: who owes which test (from the plan files)

- **Nour (C):** T-01 (with B), T-02, T-04, T-05, T-07, T-12, T-18, T-21, T-22.
- **Maha (D):** T-03, T-06, T-08, T-09 (with A), T-11, T-13, T-20, T-24, T-29.
- **Joudy (A):** T-09, T-10.
- **Aabed (E):** T-15 (needs the Compose stack in the test), T-25, T-26 (after E9), T-28 (after E4).
- **Aabed (B):** T-01 (with C), T-14 (after D6), T-27 (after the web app).
