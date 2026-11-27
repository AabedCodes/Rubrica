# AI-assisted development policy

Owner: E. Applies to every member and every coding assistant used on Rubrica. This file is the basis of report §5, and the tool table below is inventory row SC-51. Reviewed in PRs, with `CODEOWNERS` requiring E (and B, once their handle is in).

## 1. Why this exists

A coding assistant can read the repository, write code, run commands and, with a member's credentials, reach GitHub. It also suggests dependencies and copies patterns from what it reads. That makes it a supply-chain component (T-16 slopsquatting, T-19 leaked credentials) and a source of plausible-looking but wrong security code. We use assistants, and we treat their output as untrusted until a human has reviewed it.

## 2. Rules

The rules are in [`CLAUDE.md`](../CLAUDE.md), which assistants read automatically. In short:

| Rule | Enforced by |
|---|---|
| Never read or write `.env`, `secrets/` or credentials | `.claude/settings.json` deny rules; `.gitignore`; gitleaks pre-commit hook; CI `secrets` job (E8) |
| No new dependency without `scripts/admission_check.py` output | PR template; CI `admission` job (E8) |
| Never hand-edit lockfiles | deny rules on `uv.lock` and `package-lock.json`; `uv sync --frozen` in CI fails on drift |
| Everything pinned (actions to SHAs, images to digests) | CI `pins` job (`scripts/check_pins.py`) |
| Synthetic data only; canaries, never real payloads | `CLAUDE.md`; review |
| Protected areas (prompts, MCP tool definitions, workflows, interfaces) changed only when the task is about them | `ask` rules in `.claude/settings.json`; `CODEOWNERS` |
| Disclose AI authorship in every PR | PR template; reviewer checkbox |

## 3. What the assistant configuration does and doesn't do

`.claude/settings.json` (Claude Code) holds `deny` rules (secrets, lockfiles, `curl`, `wget`, `git push`, publishing) and `ask` rules (protected areas, adding dependencies). We checked the syntax against the Claude Code permissions documentation on 22 Nov 2026:

- Both `Bash(curl *)` and `Bash(curl:*)` are accepted; we use the current space form.
- Deny rules are evaluated before ask and allow rules, and a deny can't be overridden at another level.
- `Read` deny rules also apply to recognised file commands in Bash (`cat`, `head`, `tail`, `sed`, `tee`, redirections). They do **not** cover `grep -r`, or scripts that open the file themselves.
- Bash argument rules are documented as fragile and are **not a security boundary**. A command can reach the network or a file in ways the pattern doesn't match.
- OS-level enforcement comes from Claude Code's sandbox, which runs on macOS, Linux and WSL2. **On native Windows, commands run unsandboxed.**

So the deny rules are a guard rail against mistakes, not a wall. The real controls are the ones that don't depend on the assistant behaving:

- secrets live only in a git-ignored `secrets/` directory and reach containers as Docker secrets;
- CI scans the full history for secrets;
- `main` is protected and every change needs a review;
- lockfiles are frozen in CI;
- the assistant never holds a credential that the member doesn't already hold.

**Known gap, recorded as a finding.** Project settings load only when the assistant starts *inside* the repository. On 22 Nov the platform foundations were written by a Claude Code session started in the parent folder. That session did not load this repo's `.claude/settings.json`, so it could run `git push` and call the GitHub API with E's stored git credential. It did so to push branches, open PRs #1 and #7 and create the role issues, all at E's request. Rule from now on: **start the assistant from the repository root**, so the project rules apply.

**Manual test (each member, once).** Start the assistant from the repo root. Create a `.env` containing only `CANARY-E14-5c1d` and ask the assistant to read and print it. It must refuse. Ask it to run `curl --version`. It must refuse. Delete the `.env` and record the result in your row of the table below.

## 4. Tools in use (inventory row SC-51)

Each member fills in their own row. "Can read, write, execute" means what the tool can reach on that member's machine.

| Member | Assistant (and model) | Editor extensions | Can read | Can write | Can execute | Credentials it can reach | Rules file loaded? | Deny test passed? |
|---|---|---|---|---|---|---|---|---|
| E (@AabedCodes) | Claude Code desktop app, Claude Opus 5.5 | VS Code, Cursor (to confirm) | the folder it is started in and below | same | shell commands (Git Bash, PowerShell), git, uv, docker | git credential manager (GitHub push, API) | not in the 22 Nov session (started outside the repo, see §3) | not yet (CLI not installed) |
| A | | | | | | | | |
| B | | | | | | | | |
| C | | | | | | | | |
| D | | | | | | | | |

## 5. Review gate for AI-written changes

1. The author ticks the AI-assistance box in the PR template and names the assistant and the parts it wrote.
2. One other member reviews. For AI-written code, the reviewer reads every line (checkbox in the template) and checks:
   - every new import or package against the admission-check output;
   - every security-relevant constant (limits, TTLs, regexes, allow-lists) against `01-interfaces.md`;
   - that the tests actually exercise the control, so a failing control would make them fail.
3. `CODEOWNERS` adds the area owner as a required reviewer for identity, deploy, CI, MCP tools, prompts, the database and the assistant rules.
4. CI must be green (lint, test, pins, compose-smoke now; full gates in E8).
5. Nobody merges their own PR. The repo admin should set "Require approvals: 1" and the required status checks on `main` so this is enforced, not just agreed.

## 6. When an assistant gets something wrong

Log it. If it suggests a package that doesn't exist, save the admission-check FAIL output for report §4 (the brief wants one real case). If it writes insecure code that review catches, add a line to `docs/remediation-log.md` with source "AI assistant". If it reads or prints something it shouldn't, treat that as an incident: follow [`runbook.md`](runbook.md) and rotate whatever it saw.
