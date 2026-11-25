# X: Worklog convention (mini reports)

- **Author:** E (@AabedCodes)
- **Date finished:** 2026-11-22
- **PR / commits:** this PR
- **Threats / controls:** none
- **Feeds report sections:** §9 (contribution log); indirectly all sections
- **AI assistance:** Claude Code (Claude Opus 5.5) wrote all files, under E's direction

## What was done

- `docs/worklog/` with a README (rules and index) and `_template.md`.
- Backfilled entries for everything finished on 22 Nov: E1, E2, E3, E7, role claims, the edge proxy and E14.
- `CLAUDE.md` gains a "Mini reports" rule, so every member's coding assistant writes the entry as part of finishing a task.
- The PR template gets a worklog line.
- New CI workflow `worklog.yml`: a PR must add or change a file in `docs/worklog/`, unless it carries the `no-worklog` label.

## How

`worklog.yml` runs on `pull_request` (opened, synchronize, reopened, labeled, unlabeled). It diffs the PR's base SHA against its head SHA and looks for a changed file under `docs/worklog/` other than `README.md` and `_template.md`. Both SHAs come from the event payload and are passed in as environment variables, so no PR text reaches the shell.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Separate workflow file | a job in `ci.yml` | needs the `labeled` and `unlabeled` triggers; adding them to `ci.yml` would re-run the whole stack on every label change |
| `no-worklog` label as the escape hatch | always required | typo fixes and bumps shouldn't need an essay |
| Entry in the same PR as the work | a separate weekly summary | written while the decisions are fresh; reviewed together with the code |
| Index table in the README | rely on the file listing | quick overview by date and author for the report editor |

## Deviations from the plan or `01-interfaces.md`

None; the plan has no worklog. It supports §9 and the brief's individual-contribution requirement.

## Evidence

This PR's own `worklog` check passes, because the PR adds entries.

## Open items

- The repo admin can add `worklog` to the required status checks.
- PR #8 predates this convention; its entries are included here instead.
