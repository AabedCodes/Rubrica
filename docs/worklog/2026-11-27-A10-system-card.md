# A10: System card and disclosure statement (first draft)

- **Author:** A (@JoudyElGayar)
- **Date finished:** 2026-11-27 (draft; final version due Mon 7 Dec)
- **PR / commits:** PR not opened yet; commit on branch `A/A10-system-card` (from `main` at `cfaa661`)
- **Threats / controls:** R10 (human-approval line), C25, C28, C36; the controls table covers C02, C06, C07, C11, C14, C20–C21, C27–C28, C30–C35; T-37 (accepted risk)
- **Feeds report sections:** §7 (system card, disclosure statement), §8 (limitations table)
- **AI assistance:** Claude Code (desktop app, Claude Opus 5.5) drafted both documents, the test and this entry, under A's direction. The status of each item was checked against `main` (`git ls-tree`, migrations, compose file) rather than taken from the plan.

## What was done

- **`docs/system-card.md`:** the plan's 10-section outline.
  - Every component (§2) and every control (§7) carries a status: **Built** (merged on `main`), **In review** (open PR) or **Planned**.
  - The agent-authority table says plainly that no agent is built yet.
  - The human-approval table has a status column too.
- **`docs/disclosure.md`:** where to report (the repository's private vulnerability reporting), what to include, what we commit to (best effort), and what we ask of reporters.
- **`tests/unit/test_governance_docs.py`:** every relative link in both documents resolves; every component and control row has one of the three statuses; the "no agent is built yet" statement stays until agents exist.

## How

Status comes from `main` at `cfaa661` (after E merged #14–#16):
- **Built:**
  - D1: schema, per-service roles, forced row-level security, and `audit_log` with insert-only grants plus the `prev_hash` and `hash` columns.
  - D2 seed; D4 ingestion with the `network_mode: none` parser.
  - D5 retrieval, D7 blog indexing, D8 fetcher.
  - D9 sinks: `text_policy.py`, the fixed release-email template, CSV export.
  - E1–E3 and E7: Compose stack, networks and proxies, CI, pin checker, admission check.
  - `aibom/models.lock` with the embedding revision.
- **Built (front end):** A1 shell and npm hardening, A3 safe rendering, A2 walking-skeleton screens.
- **In review:** A5 review screen #17, §10 proposal #18, E's #7 and #8.
- **Planned:** everything else: identity, the model adapter, all agents, the MCP server, the release service, the audit hash-chain writer and verifier, alerts, pause and kill switch, SBOM, and the verification framework.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| A status on every component and control | Describe the designed system in the present tense | A's instruction: mark anything not built as planned instead of claiming it. An operator reading the card must not assume a control works |
| Audit log marked "Built (table and grants); hash-chain writer and verifier planned" | "Built" or "Planned" | The table, its columns and the insert-only grants are on `main`; nothing writes or verifies the chain yet |
| Disclosure in its own file, `docs/disclosure.md` | Inside the report; a root `SECURITY.md` | One place to link from the card and the report. `SECURITY.md` would add a root file not in the §1 layout; it can be proposed later if the team wants GitHub to surface it |
| Supersedes the unpushed branch `A/A10-governance-drafts` | Push that branch | That draft described planned controls as if built. Its §7 audit-trail, §8 and §9 drafts stay local for a later PR |
| A test on the documents | No test | Cheap, and it keeps the "every control has a status" rule from eroding as the card is edited |

## Deviations from the plan or `01-interfaces.md`

None. The plan's file is `docs/system-card.md`, and the disclosure statement is part of A10.

## Evidence

- `pytest tests/unit/test_governance_docs.py`: 5 passed. `make lint` passes (ruff: 63 files formatted). `make test`: 41 passed, 14 skipped by design (D's database tests and the network test). `make pins`: PASS.
- The documents were scanned for invisible characters: clean.
- 11 `TODO(owner)` markers remain (9 in the card, 2 in the disclosure).

## Open items

- **Owner inputs:**
  - C: provider and models; R7 retention.
  - D: data retention.
  - E: SBOM versions, monitoring thresholds, runbook link.
  - B: verification figures.
  - A9: BO2 figure.
- **Disclosure:** the repo admin enables private vulnerability reporting; the team agrees the acknowledgement time.
- **Keeping the card current:** update statuses as PRs merge (#17, #18 next).
- **minimatch override:** after #14 merges, a separate branch `A/A1-minimatch-override` from `main` with `overrides: {"minimatch": "11.0.8"}`, then `npm audit`, `make lint`, `make test`, a worklog entry and a commit. Recorded here as an open item, as A asked; not started.
