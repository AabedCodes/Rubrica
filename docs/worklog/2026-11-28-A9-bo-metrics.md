# A9: BO1–BO5 measurement script (snapshot-based)

- **Author:** A (@JoudyElGayar)
- **Date finished:** 2026-11-28 (script and tests; the real measurements wait on grading data and C10)
- **PR / commits:** PR not opened yet; commit on branch `A/A9-bo-metrics` (from `main` at `cfaa661`)
- **Threats / controls:** T-37 (via BO2), R10 (BO5: no release without approval), R9 (audit log as the source)
- **Feeds report sections:** §3 (evidence), §7 (system card limitations), §8 (residual risk R1, R4)
- **AI assistance:** Claude Code (desktop app, Claude Opus 5.5) wrote the script, the tests and this entry, under A's direction.

## What was done

`scripts/bo_metrics.py` computes the plan's business-objective measures from a snapshot of D1's tables:

| Measure | What it computes | From |
|---|---|---|
| **BO1** | hours from each assignment's `due_at` to its last grading result, and the median | `assignments`, `grading_runs`, `grading_results.created_at` (`proposed_grades` has no `created_at`) |
| **BO2** | not computed here: `--export-agent-scores` writes each submission's per-criterion agent score as `essay_id, criterion_id, score` for A4's `bo2_compare.py`, mapped to essay IDs with `--essay-map` | `grading_results` |
| **BO3** | median seconds from opening a review to approval, and from opening a manual-queue item to the manual grade | `audit_log` (instructor rows) |
| **BO4** | student questions whose next assistant reply has no referral sentence, out of all questions | `chat_transcripts.messages` |
| **BO5** | released grades with no instructor `approve_release` (or `manual_grade`) row; exit code 1 if any | `proposed_grades`, `audit_log` |

The agent score follows §7: the mean of the two attempts rounded down to 0.5. Rejected attempts are skipped.

## How

Pure functions over a JSON snapshot (`{"assignments": [...], "grading_results": [...], …}`, using the schema's column names), with a CLI that prints figures or JSON. Tests use a synthetic snapshot that exercises every measure, including edge cases:
- a question with no reply;
- a rejected attempt;
- an agent-written row that names a grade, which must **not** count as an approval.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Work from an exported snapshot, not a live database query | Connect with `backend/db/session.py` | **Conflict with `01-interfaces.md` §3.2:** no runtime role can read `grading_results`, `audit_log`, `proposed_grades` and `chat_transcripts` together; `rubrica_owner` is for migrations only, and `session()` only opens the calling service's own role. Stopped short of adding a role (see Deviations) |
| BO1 uses the last `grading_results.created_at` | `proposed_grades.created_at` | That column doesn't exist in D1's schema |
| BO2 delegated to `bo2_compare.py` (A4, #20), with an export for it | Compute BO2 here as well | One implementation of the comparison, tested in A4 |
| BO3 uses ASSUMED audit actions `open_review` and `open_manual_item` | Use the front end's timings | The plan says BO3 comes from the audit log. §8 lists actions with "…", and nothing writes these two yet |
| BO4 referral sentence `REFERRAL_SENTENCE = "Please ask your instructor"` | Hard-code it in tests only | Plan A9 says to agree a fixed sentence with C in `prompts/chat.md`; it's a named constant until then |
| BO5 counts only instructor (`actor_kind = user`) approvals | Any `approve_release` row | An agent can't approve (R10); a row an agent wrote must not make a release look approved |
| CLI exits with 1 when BO5 is not zero | Always 0 | Makes the check usable in a script or CI step |

## Deviations from the plan or `01-interfaces.md`

- **Conflict raised, not resolved: §3.2 has no role for reporting.** The proposal for D: a read-only `rubrica_report` role with `SELECT` on `assignments`, `grading_runs`, `grading_results`, `proposed_grades`, `audit_log` (read only), `chat_transcripts` and `manual_queue`. Alternatively, an export command D owns that writes the snapshot. `01-interfaces.md` was not changed.
- **BO3 needs two audit actions** written by the web app when an instructor opens a review or a manual-queue item: `open_review` with `args_redacted.proposed_grade_ids`, and `open_manual_item` with `args_redacted.queue_id`. These are for the §8 owners (C writes, E stores).
- **BO4 needs the referral sentence** agreed with C.

## Evidence

- **`pytest tests/unit/test_bo_metrics.py`: 8 passed.**
  - **BO1:** 3 h and 1 h, median 2 h.
  - **BO3:** review 120 s and 240 s (median 180 s); manual 900 s.
  - **BO4:** 1 of 3 questions answered without referral.
  - **BO5:** catches the one release named only by an agent row, and is OK without it.
  - **Agent scores:** mean(3, 4) gives 3.5; the rejected attempt is skipped.
  - **CLI:** prints the BO1 and BO5 lines and exits 1 on a BO5 failure; the export writes `E01,c1,3.5`.
- **Gates.** `make lint` passes (ruff on 64 files, plus ESLint and `tsc`). `make test`: pytest 44 passed, 14 skipped by design; Vitest 71 passed. `make pins`: PASS.

## Open items

- **D:** decide on the reporting role or the export (the §3.2 conflict above).
- **C:**
  - the real model run for T-37 and BO2 (C10);
  - the referral sentence in `prompts/chat.md`;
  - the `open_review` and `open_manual_item` audit actions, with E.
- **Then:** run `bo_metrics.py` on the demo data and the blind sample. Only those printed figures go into §8, the system card and the slides.
