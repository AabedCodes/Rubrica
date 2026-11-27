# A7: Confirmation screens, manual queue, audit view, pause switch

- **Author:** A (@JoudyElGayar)
- **Date finished:** 2026-11-28
- **PR / commits:** PR not opened yet. Commit on branch `A/A7-confirm-audit-pause`, stacked on `A/A5-review-screen` (#17), because it builds on A5's score-change mock and extracted-text view.
- **Threats / controls:** C25, C28, C30, C37, R9, R10; T-02 (appeal canary `CANARY-T02-062e`), T-05 (denial shown in the audit view)
- **Feeds report sections:** §2, §3, §6 (pause and alerts), §7 (audit-trail design)
- **AI assistance:** Claude Code (desktop app, Claude Opus 5.5) wrote the screens, the mocked routes, the tests and this entry, under A's direction. A asked for every confirmation screen to state exactly what will happen and to need re-auth wherever §10 says so.

## What was done

- **Appeals and grade-change confirmation (C25):**
  - `/courses/:id/appeals` lists the appeals.
  - `/courses/:id/proposals/:id` shows current and proposed scores side by side, with maximums and totals, **from the database response**.
  - The appeal is shown in a "Written by the student" box as plain text; the agent's rationale in a "Written by the AI assistant: check it against the submission" box through `SafeMarkdown`.
  - A link shows the submission's extracted text.
  - An "effect" line states exactly what accepting does, built only from the stored values.
  - Accept and Reject both need re-auth (§10 decide). Accepting updates the released grade and writes an audit row with before and after values.
- **Draft confirmation:** `/courses/:id/drafts` and `/drafts/:id` show the exact draft content as an "AI draft".
  - Accepting an assignment draft creates a **draft** assignment, with nothing published and no re-auth.
  - Accepting an answer-key draft replaces the key and needs re-auth (§10 "re-auth for keys").
  - Reject is available for both.
- **Manual queue:** reason codes in plain words ("Grader output failed validation", "Grading paused", …). Each item shows the extracted text (A5's view, with invisible characters marked) and a rubric form checked against the maximums. Submitting releases the grade and is audited.
- **Audit view (demo step 7):**
  - a filterable table (actor, action, decision, on behalf of), newest first;
  - the hash-chain status line;
  - E11 alerts as a banner;
  - a **Score changes** column showing before → after values from approvals and appeal decisions.

  Denials are highlighted, for example the seeded T-05 refusal (`chat-agent get_my_feedback denied E_NOT_FOUND`).
- **Pause switch (C30):**
  - Course settings: pause with a reason (re-auth) and resume (re-auth).
  - A banner on every course page while paused; students see "Grading may take longer…".
  - A grading run started while paused sends every submission to the manual queue (reason "Grading paused").
- **Mocks:** `MOCK(C7)` for appeals, proposals and drafts; `MOCK(D3)` for decide, accept and resolve; `MOCK(E11)` for audit and alerts; `MOCK(E10)` for controls and pause.
  - A new seeded **Assignment 0** (already graded and released for Student Two) carries the appeal, the proposal and a manual-queue item, so Assignment 1's A2 and A5 tests stay unchanged.
  - The grading mock now writes audit rows, honours the pause, and raises a full-marks-rate alert above 25% of a run.

## How

- **Code:** shapes in `src/types/oversight.ts`, wrappers in `oversightRoutes`, screens in `src/pages/oversight/`.
- **Pause state:** a `ControlsProvider` in the layout loads the course's controls once per course. The banner and the settings page share it, so pausing updates the banner immediately.
- **Audit:** the mock writes rows through one `writeAudit` helper, so every decision route records the same §8 fields. Score changes go into `args_redacted.score_changes` as numbers only.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Seed a separate graded Assignment 0 for the appeal, proposal and manual item | Put them on Assignment 1 | Assignment 1 is what A2 and A5 grade; a released grade there would change their counts. Three A2 tests needed small updates for the second published assignment |
| The seeded rationale claims different numbers ("total 8 / 8") from the stored proposal (6.5) | Matching numbers | Makes the C25 rule testable: the screen and the effect line must show 6.5 |
| Manual-queue resolve without re-auth | Require re-auth because it releases a grade | §10 doesn't mark resolve as re-auth. Followed §10 and raised it as a question (C28 says releasing grades needs re-auth) |
| Accepting an assignment draft creates a *draft* assignment | Publish it directly | Publishing is a separate human-approval step (R10); the effect line says so |
| Students may read the pause state (`GET /courses/{id}/controls`) | Instructors only | Students need the "grading may take longer" notice (plan A7) |
| Full-marks alert threshold more than 25% of a run (mock) | 50% | A starting value for the mock only; E11 sets the real rule |
| Score changes shown with shortened criterion IDs | Look up labels | §8 says the log holds IDs and counts, never free text; labels would need a second query |

## Deviations from the plan or `01-interfaces.md`

`01-interfaces.md` was **not** changed. Items for the next §10 proposal:

1. **`GET /grade-change-proposals/{id}`.** It's in C's plan but missing from §10's table. The shape is `GradeChangeProposal`.
2. **`GET /courses/{id}/drafts`** (list) and **`POST /drafts/{id}/reject`**.
3. **`GET /courses/{id}/controls`**, readable by members.
4. **The body of `GET /courses/{id}/audit`:** `{chain, alerts, rows}`, plus an `actor_display` label.
5. **`sent_to_manual_queue`** in the grading-run response.
6. **Question for D and E:** should `POST /manual-queue/{id}/resolve` need re-auth, since it releases a grade?

## Evidence

- **Vitest: 93 passed in 12 files**, 9 new in `src/pages/oversight/oversight.test.tsx`:
  - **Proposal (C25, T-02):**
    - the totals row reads max 8, current 4.5, proposed 6.5, although the AI rationale claims "total 8 / 8";
    - the effect line reads "…from 4.5 to 6.5 out of 8";
    - the canary is in the student box;
    - Accept requires re-auth;
    - Student Two then sees "Grade: 6.5 / 8".
  - **Drafts:** an assignment draft becomes a draft assignment without re-auth; a key draft needs re-auth.
  - **Manual queue:** 5 out of 4 is blocked; 3 and 3.5 are released, showing "6.5 / 8".
  - **Audit:** after grading and an approval with a change, the view shows "Hash chain intact", the full-marks-rate alert and "5 → 1.5". Filtering to denied leaves exactly the T-05 `get_my_feedback` row.
  - **Pause:** pause with re-auth; the banner shows on every course page; the grading run sends 3 submissions to the queue as "Grading paused"; the student notice appears; resume needs re-auth and clears the banner.
  - **Mock rules:** students get 403 on lists and 404 on per-record routes; any member can read controls; out-of-range manual scores are rejected.
- **Gates.** `make lint` passes (ESLint, `tsc`, ruff). `make test`: Vitest 93 passed; pytest 36 passed, 14 skipped by design. `make pins`: PASS.
- **Production build:** no mock traces. Source scan: no hidden characters.
- **MOCK tags:** C4 3, C5 2, C7 7, D3 9, D6 11, E10 5, E11 5, E4 9.

## Open items

- **Merge order:** #17 (A5) has to merge before this; then this PR is retargeted to `main`.
- **The six §10 items above,** for the next proposal (C, D, E).
- **Switching to the real API:** the `MOCK(C7)`, `MOCK(D3)`, `MOCK(E10)` and `MOCK(E11)` routes, as those tasks merge.
- **Audit view:** label lookups for criterion IDs could come later if the audit route returns them.
