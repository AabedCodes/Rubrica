# A2: Walking-skeleton screens

- **Author:** A (@JoudyElGayar)
- **Date finished:** 2026-11-27
- **PR / commits:** PR not opened yet. Commit on branch `A/A2-walking-skeleton-screens`, stacked on `A/A3-safe-markdown` (PR #15), which is stacked on `A/A1-react-shell` (PR #14).
- **Threats / controls:** R10, C02 (structured rubric), C20 (objective marking by code, mock side), C28 (re-auth on publish and approve), C29 (UI guards; mock enforces membership and roles), C36 (flagged first, no bulk approval of flagged grades), C07 (released feedback through SafeMarkdown), T-01 (answer key never sent to students, mock side)
- **Feeds report sections:** §2, §3, §7 (governance: human approval), §9
- **AI assistance:** Claude Code (desktop app, Claude Opus 5.5) wrote the screens, the mocked routes, the tests and this entry, under A's direction. A approved the plan (mocks for unmerged D3, D6 and C4; types marked ASSUMED; §10 gaps raised rather than invented silently).

## What was done

- **Instructor screens:**
  - Assignment list.
  - New assignment (draft).
  - Assignment page:
    - Rubric editor: rows of `{label, max_points, kind}` with validation, read-only once published.
    - Answer-key editor: text for open criteria; an exact choice, or a number with a tolerance, for objective ones.
    - Publish, behind re-auth.
  - Review list:
    - Start a grading run.
    - Proposed totals with flag badges, flagged rows first.
    - Approve the selected unflagged grades, behind re-auth.
- **Student screens:**
  - Assignment page with the rubric.
  - Submission form: text, objective answers and an optional PDF. A new submission replaces the earlier one.
  - The current submission.
  - "My grades", showing only released grades, with AI feedback labelled and rendered through `SafeMarkdown`.
- **Mocked routes**, all on one synthetic course:
  - `MOCK(D6)`: content and submission routes (10 tags).
  - `MOCK(C4)`: grading runs and the proposed-grade list.
  - `MOCK(D3)`: approve-and-release.
  - The grading mock follows §7: objective criteria marked by code, two attempts, the proposed score as the mean rounded down to 0.5, totals computed by code, and `full_marks` and `disagreement` flags.
  - The seeded submission with the demo canary `CANARY-T04-7f3a` plays a fooled grader. It gets full marks and the `full_marks` flag, so the review list shows how C36 surfaces it.

## How

- **Types and wrappers.** Typed wrappers are in `src/endpoints.ts`. Request and response shapes are in `src/types/content.ts` and `src/types/grading.ts`, every one marked `ASSUMED`.
- **Mock code** lives in `src/mocks/`:
  - `state.ts`: the synthetic world.
  - `content.ts` and `grading.ts`: the route handlers.
  - `access.ts`: the C29 rules. Students never see drafts; assignments in other courses are "not found".
  - `mockApi.ts`: auth, then hands each request to the handlers.
- **Data loading.** Pages load through a small `useLoad` hook, with each loader wrapped in `useCallback`. Re-auth isn't special-cased anywhere in the screens: the A1 client opens the modal on `401 reauth_required` and retries once.
- **Routes.** `App.tsx` maps built screens through `SCREEN_ELEMENTS`; the rest still show their task's placeholder. The A5 detail route is already registered and shows a placeholder.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Max points: more than 0, at most 100, a multiple of 0.5 | Any positive number | §3.1 requires `> 0`; §7 moves scores in steps of 0.5, so maximums should too. 100 is an ASSUMED upper bound to catch typos |
| Rubric read-only once published (mock rejects it; UI shows a table) | Editable after publishing | Changing criteria after students have submitted would invalidate grading. ASSUMED; D decides the real rule |
| Saving a rubric clears the old answer key (mock) | Keep the old key | Criterion IDs change, so the old key no longer matches. Flagged for D |
| Multipart for submissions (`body_text`, `objective_answers` as JSON, `file`) | JSON plus a separate upload | D6 says text, an optional PDF and `objective_answers` in one route |
| A 10 MB client-side PDF limit and a PDF-only check | No check | Fails early for the user; the server must still enforce its own limit (ASSUMED value) |
| Flagged grades can't be bulk-selected, only opened (plan A5) | Approve-all button | C36: "approving without reading" is the residual risk; the plan says flagged grades are approved only from their detail view |
| "My grades" uses `GET /assignments/{id}/my-submission` per assignment | A new `GET /courses/{id}/my-grades` | Uses a route §10 already has instead of inventing one. A grade appears only once released (R10) |
| `noValidate` on the rubric and key forms | The browser's native validation | Native bubbles (from `min=0.5`) blocked the submit before our clearer messages could show. A test caught this |
| Deadline check (`open`) worked out in the loader | `Date.now()` during render | The React purity lint rule fails on impure calls in render; the server enforces the deadline anyway |

## Deviations from the plan or `01-interfaces.md`

`01-interfaces.md` was **not** changed. The screens need these, which §10 doesn't define:

1. **No request or response bodies** for any content or grading route. The assumed shapes are in `src/types/*.ts`.
2. **Missing routes:**
   - `GET /courses/{id}/assignments` and `GET /assignments/{id}`. Every assignment screen needs these.
   - `GET /assignments/{id}/answer-key`, instructor only. §10 has only `PUT`.
3. **No route to accept an instructor-written answer key.** D6 says acceptance goes through the release service with re-auth, but no API route triggers it. The UI shows the key as "draft" and says the route isn't defined yet.
4. **Approving vs. releasing.** It's assumed that `POST /proposed-grades/approve` hands grades to the release service, which releases them at once. §3.1 has separate `approved` and `released` statuses, so D should confirm.
5. **New error code `deadline_passed`** for submissions after `due_at`.

These go into the §10 proposal (open item), tagging D (content, release) and C (grading runs).

## Evidence

- **Vitest: 71 passed in 9 files** (20 new A2 tests on top of A1 and A3):
  - **`src/pages/assignments/walkingSkeleton.test.tsx`**, through the real screens:
    - The instructor creates a draft. A blank label and 0 points are rejected with messages. They fix the rubric, add an objective criterion, save the key (status "draft"), and publish through the re-auth modal (`staleReauth`, C28). The rubric is then read-only.
    - **End to end:** a student submits text, an objective answer and a PDF. The instructor runs grading: 4 submissions, flagged first, and Student Four's checkbox is disabled with the "Full marks" badge. They approve Student One through re-auth. The student then sees the grade in "My grades", with AI-written feedback labelled.
    - Unreleased grades are invisible to the student.
    - A non-PDF attachment is refused before sending.
  - **`src/mocks/content.test.ts`** (the mock enforces C29 so screens can't come to rely on data they won't get):
    - Students get 403 on the answer key, and the key's text never appears in the assignment they receive (T-01).
    - Drafts are hidden from students as 404.
    - Students get 403 on create, grading runs, proposed grades and approve.
    - `max_points = 0` is rejected.
    - Approve needs re-auth when the code is stale.
    - Objective marking and totals are done by code; the canary submission is flagged `full_marks`; a second run doesn't regrade.
  - **`src/rubric.test.ts`:** rubric and answer-key validation cases.
- **Gates.** `make lint` passes (ESLint, `tsc`, ruff). `make test`: Vitest 71 passed; pytest 36 passed, 14 skipped by design. `make pins`: PASS.
- **Production build:** no mock traces in `dist/` (`CANARY-T19`, `CANARY-T04`, `mock-csrf`, `example.test` and the mock names all absent).
- **Browser check:** in mock mode on the dev server, signed in as the instructor, started a run. The review list shows Student Four (10/10, "Full marks") and Student Three ("Attempts disagree") first with disabled checkboxes, and the console has no errors.

## Open items

- **§10 proposal PR** covering the A1 and A2 gaps above. It needs your OK to open; it tags E, D and C.
- **Switching to the real API.** As D6, D3 and C4 merge, switch each `MOCK(...)` route to the real one (`grep -rn "MOCK(" frontend/src`) and adjust the `ASSUMED` types to whatever §10 ends up saying.
- **Next screens.**
  - A5 replaces the review-detail placeholder and adds per-criterion score changes to approve.
  - A8 turns the end-to-end test into the Playwright `tests/e2e/test_main_workflow.spec.ts` against the real stack.
- **Not built yet.** The review list has no `outlier` flag (§7 computes it when the review screen loads; A5) and no CSV export link (D's export route).
- **Inherited:** the minimatch advisory bump, the frontend CI job (E), and `web` serving the build.
