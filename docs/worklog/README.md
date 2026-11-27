# Worklog: mini reports

Every time a task, or a meaningful piece of one, is finished, its author writes a short **mini report** here, **in the same PR as the work**. At the end we build the Final Security Report from these files instead of reconstructing three weeks from memory and git history. They also serve as evidence of individual contribution (report §9 contribution log).

CI enforces this: the `worklog` check fails on a PR that adds or changes no file in `docs/worklog/`. For PRs that genuinely need no entry (a typo fix, a dependency bump with nothing to decide), add the label `no-worklog`.

## Rules

- **One file per finished task or piece**, named `YYYY-MM-DD-<task-id>-<short-slug>.md`. Examples: `2026-11-22-E2-compose-stack.md`, `2026-11-25-D1-schema-and-rls.md`, `2026-11-26-C3-mcp-server-skeleton.md`. Use `X` as the task ID for work outside the plan, for example `2026-11-22-X-role-claims.md`.
- **Copy [`_template.md`](_template.md)** and fill in every section. Write "none" rather than deleting a section.
- **Record the small decisions.** Thresholds, versions chosen, things tried that failed, and deviations from `01-interfaces.md` or your plan file. These are what the report and the Q&A ask about, and they're the first thing forgotten.
- **Link evidence**: PR, commits, CI run, test names, command output.
- **Say which report sections it feeds** (§1 to §9), so the section editor can collect them.
- **If an AI assistant wrote part of it**, say which assistant and which parts, the same as in the PR template.
- Fix an entry by editing it in a later PR. Don't delete history.

## How the final report uses them

Each section owner (see `docs/plan/README.md`, "Milestone 2 deliverables and owners") filters this folder by the "Feeds report sections" line and turns the entries into prose. B, as editor, checks that every Critical and High threat in the matrix links to at least one entry.

## Index

Add a line for your entry here, newest first.

| Date | Task | Entry | Author |
|---|---|---|---|
| 2026-11-28 | E8 | [Frontend CI job and enforced review gate](2026-11-28-E8-frontend-ci-and-review-gate.md) | E |
| 2026-11-27 | A2 | [Walking-skeleton screens](2026-11-27-A2-walking-skeleton-screens.md) | A |
| 2026-11-27 | A3 | [SafeMarkdown and the HTML-sink lint rule](2026-11-27-A3-safe-markdown.md) | A |
| 2026-11-27 | A1 | [React shell and npm hardening](2026-11-27-A1-react-shell.md) | A |
| 2026-11-26 | D7 | [Course blog indexing](2026-11-26-D7-blog-indexing.md) | D |
| 2026-11-26 | D8 | [Citation fetch service](2026-11-26-D8-citation-fetch-service.md) | D |
| 2026-11-26 | D4 | [Isolated document ingestion](2026-11-26-D4-document-ingestion.md) | D |
| 2026-11-26 | D5 | [Course-scoped retrieval](2026-11-26-D5-scoped-retrieval.md) | D |
| 2026-11-26 | D8 | [Citation URL preflight](2026-11-26-D8-citation-url-preflight.md) | D |
| 2026-11-22 | X | [Worklog convention (this folder)](2026-11-22-X-worklog-convention.md) | E |
| 2026-11-22 | E14 | [AI-assisted development policy, runbook, report drafts](2026-11-22-E14-policy-runbook-drafts.md) | E |
| 2026-11-22 | E2 | [Edge proxy: egress gap on Docker Desktop](2026-11-22-E2-edge-proxy.md) | E |
| 2026-11-22 | X | [Role claims](2026-11-22-X-role-claims.md) | E |
| 2026-11-22 | E7 | [Package admission check](2026-11-22-E7-admission-check.md) | E |
| 2026-11-22 | E3 | [CI skeleton and pin checker](2026-11-22-E3-ci-skeleton.md) | E |
| 2026-11-22 | E2 | [Compose stack, networks, hardening](2026-11-22-E2-compose-stack.md) | E |
| 2026-11-22 | E1 | [Repository skeleton](2026-11-22-E1-repo-skeleton.md) | E |
