# X: Role claims on GitHub

- **Author:** E (@AabedCodes)
- **Date finished:** 2026-11-22
- **PR / commits:** #7 (d79e2e9); issues #2 to #6
- **Threats / controls:** C16 (workflow hardening)
- **Feeds report sections:** §5.1, §9 (who owned what)
- **AI assistance:** Claude Code (Claude Opus 5.5) wrote the workflow and created the issues and labels, under E's direction

## What was done

- One issue per role, labelled `role` plus `unclaimed` or `claimed`: A #2, B #3, C #4, D #5, E #6. E (@AabedCodes) is pre-claimed.
- `.github/workflows/role-claims.yml`: commenting `/claim` assigns the commenter, swaps the label, appends "— claimed by @handle" to the title and replies with next steps. `/unclaim` reverses it, for the claimant or the repo owner.
- A README "Team roles" section.

## How

The workflow is triggered by `issue_comment` and runs only on issues labelled `role`. It uses `actions/github-script` (pinned to the v8.0.0 SHA). The comment text is read from the event payload in JavaScript, never interpolated into a shell, so it can't be used for injection. Its token has `issues: write` only.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Issues plus a comment command | a `TEAM.md` the bot edits; GitHub Projects | `main` is protected, so a bot can't push to it; issues need no write access to code |
| Only collaborators can claim (`author_association`); one role per person | anyone can claim | invitees who haven't accepted would otherwise race each other |
| The CODEOWNERS update is left to the claimant's own PR | bot edits CODEOWNERS | same protected-branch reason, and the change is reviewed |

## Deviations from the plan or `01-interfaces.md`

None; this is outside the plan.

## Evidence

The issues exist with the right labels, and #6 is assigned to @AabedCodes. PR #7's CI is green.

## Open items

- `/claim` only works after #7 is merged, because `issue_comment` workflows run from the default branch.
- The `/claim` flow hasn't been exercised by a real comment yet.
