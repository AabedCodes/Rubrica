# X: §10 API contract proposal

- **Author:** A (@JoudyElGayar)
- **Date finished:** 2026-11-27
- **PR / commits:** PR not opened yet; commit on branch `A/X-api-contract-proposal` (from `main`)
- **Threats / controls:** C27, C28, C33 (fixed error codes extended to the web API), C36, R10, T-01 (answer key instructor-only), T-05 (404 rather than 403 for others' records)
- **Feeds report sections:** §2, §9
- **AI assistance:** Claude Code (desktop app, Claude Opus 5.5) drafted the `01-interfaces.md` changes and this entry from the shapes the A1, A2 and A5 front end assumes. A asked for the proposal and reviews it before it goes to the owners.

## What was done

A proposal PR to `01-interfaces.md` §10, the shared contract. It changes no code. It contains:

- **New routes in the §10 table:**
  - `GET /courses/{id}/assignments`, `GET /assignments/{id}`, `GET /assignments/{id}/answer-key` and `POST /assignments/{id}/answer-key/accept` (owner D);
  - `GET /proposed-grades/{id}` (owner C).
- **"(re-auth)"** added to publish, which A2's plan already treats as re-auth.
- **§10.1 Conventions:**
  - the error body `{"error": "<code>"}` with a fixed code list;
  - 404 for records the caller can't see;
  - multipart for the two upload routes;
  - model-written text rendered only through the safe Markdown component.
- **§10.2 Request and response bodies** for auth, assignments and keys, submissions, grading and review.
- **§10.3 Open questions** that only the owners can decide.

## How

The shapes are copied from the front end's `ASSUMED` types (`frontend/src/apiTypes.ts`, `src/types/content.ts`, `src/types/grading.ts`) on the A1, A2 and A5 branches (PRs #14, #16, #17), with field names checked against §3.1. Owners are the section owners from §10's table: E for auth, D for content, submissions, approve and release, C for grading runs and the review detail.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| One PR for all the §10 gaps, separate from the screen PRs | One proposal per screen PR; let backend owners define the shapes | D and C are building these routes now. One place to agree them avoids rework, and the screen PRs don't wait on it |
| Branch from `main`, not from the screen stack | Stack it on #17 | Owners can review and merge the contract on its own; it doesn't depend on any front-end code |
| Web API errors follow the MCP server's C33 rule (fixed codes, no echoed text) | Free-text error messages | Same threat (error text as an injection or information channel), same fix; the front end maps codes to its own wording |
| 404 for per-record routes when the caller can't see the record | 403 | The A5 mock leaked existence with 403; a test caught it. Matches `E_NOT_FOUND` in §5 |
| New route `POST /assignments/{id}/answer-key/accept` | Reuse `POST /drafts/{id}/accept` | D6 says instructor-written keys are accepted through the release service with re-auth, but nothing triggered it. Drafts are for agent proposals (C7) |
| Open questions listed in §10.3 instead of decided | Decide them in the front end | They're D's decisions (release semantics, rubric locking, limits); the front end shouldn't set them silently |

## Deviations from the plan or `01-interfaces.md`

This PR *is* the change to `01-interfaces.md`, §10 only. It is a protected file (CLAUDE.md), and the task is about it. It needs the section owners' review: E for auth and errors, D for content, submissions and release, C for grading runs and detail. The front-end branches still say `ASSUMED` until this merges, and will be updated to whatever the owners change here.

## Evidence

- `git diff` of `01-interfaces.md`: §10 table rows plus the new §10.1–10.3. No other section changes, so there is no overlap with E's open PR #8, which edits §2 only.
- The file was scanned for invisible characters: none, after A5's experience with the editing tool.
- The shapes in §10.2 match the front-end types that PRs #14, #16 and #17 test against: 84 Vitest tests, including the mock's access rules.

## Open items

- **Owner answers** to the four §10.3 questions (D), and review of the error-code list (E).
- **Not covered yet:** the routes A6 and A7 will need (chat, appeals, blog, materials list, drafts and proposals, manual queue, audit, alerts, pause state). A follow-up proposal once those screens are planned.
- **Follow-through:** once merged, drop the `ASSUMED` markers in the front-end types and adjust the mocks to any changed shapes.
