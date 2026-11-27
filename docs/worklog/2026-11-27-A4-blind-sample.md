# A4: Blind hand-grading sample for BO2 (prepared, not yet graded)

- **Author:** A (@JoudyElGayar)
- **Date finished:** 2026-11-27 (preparation; the hand grading is a teammate's step)
- **PR / commits:** PR not opened yet; commit on branch `A/A4-blind-sample` (from `main` at `631c357`)
- **Threats / controls:** T-37 (the accepted risk: believable but wrong in-range scores), BO2
- **Feeds report sections:** §3 (verification evidence), §8 (residual risk R1), §7 (system card limitations)
- **AI assistance:** Claude Code (desktop app, Claude Opus 5.5) wrote the 12 synthetic essays, both scripts, the tests and this entry, under A's direction. A approved the plan: D reviews `seed/`, E reviews `scripts/`, and the blind sheet never shows agent scores.

## What was done

- **`seed/bo2/essays.json`:** 12 synthetic, team-written essays for one task ("identify a trust boundary in agent-assisted grading and propose a control"), with two open criteria of 5 points each.
  - They vary deliberately: off-topic, vague, generic network security, partially right, one criterion strong and the other weak, full answers with justification.
  - The intended quality of each essay is **not** recorded anywhere, so the file can't hint at a score.
- **`scripts/bo2_blind_sheet.py`:** builds, from the essays file only, the following:
  - `seed/bo2/blind_packet.md`: essays in a shuffled order under opaque sample IDs (`S-` plus 6 hex characters), with the task and rubric, and the instruction to grade before looking at any agent score.
  - `seed/blind_grades.csv`: one empty row per sample and criterion. This is the plan's file name.
  - `seed/bo2/sample_map.json`: sample ID to essay ID, read only by the comparison.

  It refuses to overwrite an existing sheet, which may already hold scores.
- **`scripts/bo2_compare.py`:** run after grading.
  - Reads the filled sheet, the map, and an agent-scores CSV (`essay_id, criterion_id, score`).
  - Prints n, BO2 (the share of agent criterion scores within one point of the blind score), the per-criterion share, the mean absolute difference, and the "confidently wrong" cases. It can also print JSON.
  - Refuses an unfinished sheet, missing agent scores, or scores outside 0 to the maximum or off the 0.5 grid.
- The empty sheet and packet are generated and committed, so the grader can start straight away.

## How

The blind sheet can't show agent scores **by construction**: the generator's only input is the essays file, and agent scores don't exist until a run on the real model (A9). The shuffle orders by the opaque ID, a SHA-256 of a salt plus the essay ID, so it is deterministic, needs no randomness, and doesn't follow the file's order. The salt is a flag (`rubrica-bo2-v1` by default). The comparison joins blind and agent scores through the sample map.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Write new synthetic essays instead of using D2's submissions | Use the seeded submissions | D2's seed holds one-line placeholders ("Synthetic explanation 3 for course 1."), not essays that vary in quality, so BO2 would measure nothing |
| No quality label stored with the essays | Store the intended band to sanity-check results | A grader opening the file would see the intended answer; the comparison only needs the two sets of scores |
| "Confidently wrong" means a gap of 2 or more points (`CONFIDENT_GAP`) | 1.5; a z-score | A starting threshold, recorded here and in the script; with 5-point criteria, 2 points is a different grade band. BO2's own threshold is the plan's "within one rubric point" |
| The agent-scores input is a CSV export, not a database query | Read `grading_results` directly | `grading_results` isn't being written yet (C5 planned); a CSV keeps the script testable now and works with any export |
| The empty sheet is committed | Generate it on the grader's machine | One shared sample ID set, reviewable in the PR; the grader commits their scores to the same file |
| SHA-256 ordering instead of `random.shuffle` | `random` with a seed | Deterministic and reviewable; also avoids ruff's S311 rule (pseudo-random generator) |

## Deviations from the plan or `01-interfaces.md`

- **The plan's A4 says to choose seeded essays "with D".** D2's seed has no essays, so A wrote them. They sit in `seed/bo2/`, D's area, and need D's review. Loading them into the database (`make seed`), so the real model can grade them for A9, means a change to D's `seed/generate.py`. That is left to D.
- **Two new files in `scripts/`,** E's area under CODEOWNERS, so they need E's review. The plan's A9 also puts `scripts/bo_metrics.py` there.

## Evidence

- `pytest tests/unit/test_bo2.py`: 12 passed. They prove:
  - the essays have unique IDs, vary in length, and carry no quality field;
  - the sheet has 24 empty rows with exactly the expected columns;
  - nothing the script adds around the essays mentions proposed scores, attempts, validator results or flags, and no essay ID appears in the packet;
  - the order is shuffled and the IDs are opaque;
  - the generator refuses to overwrite a sheet;
  - on synthetic numbers, the comparison gives BO2 = 20/24, finds exactly one confidently wrong essay, and gives 10/12 within one point per criterion;
  - an unfinished sheet, a missing agent score and out-of-range scores are rejected.
- `make lint` passes (ruff on 65 files). `make test`: 48 passed, 14 skipped by design. `make pins`: PASS.
- The generated sheet has 24 rows and 0 filled scores. All files were scanned for invisible characters: clean.

## Open items

- **Who grades:** a teammate who is **not C** fills `seed/blind_grades.csv` from `seed/bo2/blind_packet.md`, before seeing any agent score, then commits it. The team names the grader.
- **D:** review `seed/bo2/essays.json`; load the 12 essays as submissions to a BO2 assignment in `make seed` so a grading run can score them (A9).
- **E:** review `scripts/bo2_blind_sheet.py` and `scripts/bo2_compare.py`.
- **A9:** export the agent's per-criterion scores to CSV after a real-model run, run `bo2_compare.py`, and report n, the share and the confidently wrong cases. The report must say these are synthetic essays graded by a student acting as instructor.
- **minimatch override:** after #14 merges, on its own branch (see the A10 entry).
