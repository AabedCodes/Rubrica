# §5 Development pipeline security (draft)

Owner: E; every member contributes their tool row. The brief asks for: the CI security gates, and the AI-assisted development policy, covering tools used, their read/write/execute scope, the rules and configuration files and how they were reviewed, and the review gate for AI-authored changes. The policy itself is [`docs/ai-assisted-development.md`](../ai-assisted-development.md); this section summarises it with evidence.

## 5.1 Source control

- `main` is protected: changes arrive by pull request only, with no force-push and no deletion. **TODO (repo admin):** turn on "Require approvals: 1" and require the status checks `lint`, `test`, `pins` and `compose-smoke`. As of 22 Nov these weren't enforced: PR #7 showed as mergeable with zero reviews.
- `CODEOWNERS` names the required reviewer per area (deploy, CI, identity, scripts, the AI-BOM, the assistant rules: E; MCP and prompts: C; database: D). The B, C and D handles are added when each member claims their role issue.
- The PR template asks for threat and control IDs, AI assistance (which tool, which parts), admission-check output for new dependencies, and has a reviewer checkbox "I read every AI-written line".
- gitleaks runs as a pre-commit hook locally; CI is the real gate (E8).

## 5.2 CI gates

| Job | Fails the build when | Status |
|---|---|---|
| `lint` | ruff finds an error or unformatted code; `uv.lock` is stale | done |
| `test` | any unit, authz or deterministic verification test fails (`LLM_PROVIDER=fake`) | done |
| `pins` | an action isn't pinned to a 40-hex SHA; an image or `FROM` has no digest; a lockfile is missing | done |
| `compose-smoke` | `make up` doesn't reach all-healthy; any egress or isolation check fails | done |
| `deps` | OSV-Scanner, pip-audit or npm audit report a High or Critical finding not in `security/accepted-findings.yaml` | TODO (E8) |
| `secrets` | gitleaks finds anything in the full history | TODO (E8) |
| `models` | a pickle-based model file, a checksum mismatch or a ModelScan finding | TODO (E8) |
| `admission` | a lockfile changes without admission output for each new package in the PR body | TODO (E8) |
| `images` | Trivy finds a High or Critical issue with a fix available | TODO (E8) |
| `sbom` | the CycloneDX generation or merge fails | TODO (E8) |

Workflow hardening (C16): the top-level token has `permissions: contents: read`; checkout uses `persist-credentials: false`; `pull_request_target` is never used. The role-claim workflow has `issues: write` only and reads the comment text inside JavaScript, never in a shell.

## 5.3 AI-assisted development

Summarise §§2–5 of the policy here:
- the rules table;
- what the deny rules do and don't enforce (they are a guard rail, not a sandbox; there is no OS sandbox on native Windows);
- the per-member tool table (SC-51);
- the review gate.

Include the finding from 22 Nov: the assistant session that built the foundations was started outside the repo, so the project's deny rules weren't loaded. It pushed and used the GitHub API with E's credential, at E's request. Since then, the rule is to start assistants from the repo root.

TODO: each member's deny-rule test result, and one example of a review comment that caught an AI mistake.
