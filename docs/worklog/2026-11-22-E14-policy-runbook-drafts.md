# E14: AI-assisted development policy, runbook, report drafts

- **Author:** E (@AabedCodes)
- **Date finished:** 2026-11-22 (first version; the report drafts keep growing until 7 Dec)
- **PR / commits:** #8 (06500a8)
- **Threats / controls:** T-16, T-19 · C14, C16
- **Feeds report sections:** §4, §5, §6
- **AI assistance:** Claude Code (Claude Opus 5.5) wrote all files, under E's direction

## What was done

- `docs/ai-assisted-development.md`:
  - each rule and what enforces it;
  - what the `.claude` deny rules do and don't cover;
  - the SC-51 tool table (one row per member);
  - the review gate;
  - a 2-minute deny test for each member.
- `docs/runbook.md`: one page covering detect, triage, contain, recover and communicate, with a message template. Steps that depend on E9 to E11 are marked, with fallbacks.
- `docs/report/04-supply-chain.md`, `05-pipeline.md`, `06-monitoring.md`: drafts with TODO markers, including the per-service blast-radius table.
- `docs/remediation-log.md` (Appendix D columns), with three findings.
- `.claude/settings.json`:
  - current `Bash(cmd *)` syntax;
  - denies `npm publish` and `uv publish`;
  - `ask` rules for workflows, prompts, MCP tool files, interfaces, the assistant rules, `uv add` and `npm install`.

## How

We checked the deny-rule syntax against the Claude Code permissions and sandboxing docs on 22 Nov:
- both `cmd:*` and `cmd *` forms work;
- deny is evaluated before ask, and ask before allow;
- `Read` denies also cover `cat`, `head`, `tail` and `sed`, but not `grep -r` or scripts;
- Bash argument rules are fragile and not a security boundary;
- the OS sandbox exists on macOS, Linux and WSL2, but not on native Windows.

The policy therefore presents the rules as guard rails and names the controls that don't depend on the assistant.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Protected areas are `ask`, not `deny` | deny | the people who own those areas need to edit them with an assistant; ask forces a conscious yes |
| `uv add` and `npm install` are `ask` | allow | forces a pause to run the admission check first |
| No `sandbox` block in settings yet | add one | the exact keys weren't verified, and it does nothing on native Windows; listed as a TODO |
| Runbook names fallbacks for tooling that isn't built yet | wait for E10 and E11 | usable from day one |

## Deviations from the plan or `01-interfaces.md`

None.

## Evidence

- **Finding:** the 22 Nov assistant session was started outside the repo, so `.claude/settings.json` wasn't loaded, and it could `git push` with E's credential (at E's request). Logged as remediation row 3; the rule is now to start assistants from the repo root.
- The deny test wasn't run: the Claude Code CLI isn't installed on E's machine.

## Open items

- Every member fills in their SC-51 row and runs the deny test.
- The report drafts get filled in as E8 to E12 land.
- Time a tabletop run of the runbook once E10 and E11 exist.
