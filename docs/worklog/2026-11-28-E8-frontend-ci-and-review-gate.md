# E8 (part): frontend CI job and enforced review gate

- **Author:** E (@AabedCodes)
- **Date finished:** 2026-11-28
- **PR / commits:** this PR (frontend job); branch protection on `main` set through the GitHub API on the same day
- **Threats / controls:** T-10, T-16, T-17 · C07, C14, C16
- **Feeds report sections:** §5.1, §5.2
- **AI assistance:** Claude Code (Claude Opus 5.5) wrote the job, applied the protection settings and wrote this entry, under E's direction

## What was done

- New CI job `frontend`, on Node 22 (the version the frontend's `engines` field requires):
  - `npm ci --ignore-scripts`
  - `npm run lint` (includes A3's C07 HTML-sink rule)
  - `npm test` (Vitest)
  - `npm run build` (typecheck and build)
  - `npm audit --audit-level=high`
- Branch protection on `main` is now enforced. The repo moved to `AabedCodes/Rubrica`, so E is admin.
  - Pull requests only, with 1 approving review.
  - Approvals are dismissed when new commits are pushed.
  - Required status checks: `lint`, `test`, `pins`, `compose-smoke`, `worklog`, plus `frontend` once this PR is merged.
  - The rules apply to admins too. No force-pushes, no deletion.
- The onboarding prompt points to the new repo URL.

## How

`actions/setup-node` is pinned to the v7.1.0 commit SHA, consistent with C16, and `check_pins.py` passes. The protection settings went through `PUT /repos/AabedCodes/Rubrica/branches/main/protection`, then were read back with a GET to confirm what is actually enforced.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| CI found that frontend tests had never run | — | A's PRs #14–#16 cited 84 Vitest tests, but `ci.yml` had no Node step. Found while reviewing #17 |
| `npm audit` gate at High | Moderate; no audit | matches the E8 `deps` rule; today's only finding is moderate (minimatch via typescript-eslint, dev-only) |
| Dismiss stale approvals | keep approvals across pushes | a force-push after approval (#14–#16) then needs a fresh look. We checked those by hand by comparing tree SHAs; now GitHub enforces it |
| Rules apply to admins (`enforce_admins`) | let admins bypass | otherwise the gate isn't real; the brief grades a working review gate. Turn it off only temporarily, with a note here, if the team is ever blocked |
| Code-owner review not required yet | require it | B, C and D handles aren't in `CODEOWNERS` yet, so E would be the only owner of most paths and couldn't get their own PRs approved. Switch it on once the handles are filled in |
| `frontend` added to required checks only after this PR is merged | add it now | a required check that never reports would block every open PR that doesn't have the job yet |
| Branches don't have to be up to date before merging (`strict: false`) | require it | constant rebasing for 5 people; CI runs on the merge ref anyway |

## Deviations from the plan or `01-interfaces.md`

None. This is part of E8, done early.

## Evidence

- The protection read-back is in this PR's description.
- The `frontend` job's first run on this PR.
- A local run on 27 Nov, Node 26 with the engine check relaxed:
  - 75 of 84 tests pass;
  - the 9 failures are a Windows-only path bug in `lintRules.test.ts`, reported on #17;
  - lint and build pass.

## Open items

- Add `frontend` to the required checks after merge.
- Require code-owner reviews once `CODEOWNERS` has every handle.
- The rest of E8: the `deps`, `secrets`, `models`, `admission`, `images` and `sbom` jobs.
- A fixes the Windows path in `lintRules.test.ts`.
