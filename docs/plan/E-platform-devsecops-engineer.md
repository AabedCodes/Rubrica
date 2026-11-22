# Person E · Platform & DevSecOps Engineer

You build the ground everything runs on and the rails it runs along: the repository, the Compose deployment, identities and credentials, the CI pipeline and its gates, the SBOM, the supply-chain task, monitoring, the kill switch and the runbook. Three of the M2 rubric's areas are mostly yours (supply chain 15, pipeline 5, monitoring and incident response 15), and the Week 13 advisory drill is yours to lead.

Read `README.md` and `01-interfaces.md` first. Sections 1, 2 and 4 of `01-interfaces.md` are yours, and so is the auth part of §10.

## What you own

| Kind | Items |
|---|---|
| Controls | C10 limits and budget caps (C adds the hook in the model adapter), C11 audit log storage, hash chain and alerts (C writes tool-call rows), C12 scoped credentials and private storage (C handles prompt minimisation), C14 package admission and isolated worker, C15 model pinning in CI (D loads and checks at runtime), C16 pinned CI actions and images, C27 passwords, rate limits and instructor second factor, C28 short sessions and re-auth, C30 kill switch (with C and A), C32 agent capability tokens |
| Requirements | R6 roles and agent identities, R9 CI gates (C writes the tool-call audit rows), R11 SBOM and AI-BOM |
| Verification tests | T-15, T-16, T-17, T-19, T-25, T-26, T-28, T-30, T-31 |
| Report | §4 supply-chain remediation, §5 pipeline and AI-assisted development, §6 monitoring and incident response (C writes the agent-stopping part) |
| Other deliverables | SBOM and remediation log, the README's run instructions, the Week 13 advisory note |
| Demo | Step 8 (one supply-chain finding, before and after) and the kill switch if time allows |

## Timeline

| ID | Task | Due | Depends on |
|---|---|---|---|
| E1 | Repository, branch protection, CODEOWNERS, PR template, Makefile, `CLAUDE.md` | **Mon 23 Nov** | — |
| E2 | Compose stack, networks, proxies, container hardening | **Tue 24 Nov** | E1 |
| E3 | CI skeleton (tests + lint) | Tue 24 Nov | E1 |
| E4 | Identity: login, TOTP, sessions, CSRF, re-auth | Wed 25 Nov | D1 |
| E5 | Capability tokens and service secrets | Wed 25 Nov | D1 |
| E6 | Audit library with hash chain | Wed 25 Nov | D1 |
| E7 | Admission check script, shown on a real case | Thu 26 Nov | E1 |
| E8 | Full CI gates, pinning checks, SBOM and AI-BOM | Mon 30 Nov | E3 |
| E9 | Limits and budget caps | Tue 1 Dec | E4; C1 |
| E10 | Kill switch and course pause | Tue 1 Dec | C3; A's button |
| E11 | Alert rules and the audit chain verifier | Wed 2 Dec | E6 |
| E12 | First full scan, remediation log, at least one real fix with before-and-after | Thu 3 Dec | E8 |
| E13 | All your verification tests merged | **Fri 4 Dec** | B: framework |
| E14 | Runbook, AI-assisted development policy, report §4–§6 | Mon 7 Dec | — |
| E15 | Clean-machine README run with a teammate | Tue 8 Dec | everything |
| E16 | Advisory drill readiness (practice run), then the real drill | practice by Wed 2 Dec · drill in Week 13 | E8 |

---

## E1 · Repository (Mon 23 Nov)

1. Create the repository with the layout in `01-interfaces.md` §1. Commit an empty skeleton so everyone can start in the right folders.
2. Protect `main`: pull requests required, one approving review, status checks required, no force-push, no deletion.
3. `CODEOWNERS`:

   ```
   /01-interfaces.md                         @B @C @D @E          # (use GitHub handles)
   /deploy/  /.github/  /backend/identity/   @E
   /backend/mcp_server/  /prompts/           @C
   /tests/unit/snapshots/mcp_tools.json      @C @B
   /backend/db/                              @D
   /CLAUDE.md  /.claude/                     @E @B
   ```

4. `.github/pull_request_template.md` with: what changed; threat or control IDs touched; "Did an AI assistant write any of this? Which one, and which parts?"; "New dependency? Paste `admission_check.py` output"; reviewer checkbox "I read every AI-written line".
5. `Makefile` targets from `01-interfaces.md` §1. `make up` must work on a clean machine with only Docker and `make`.
6. `.env.example` with every variable and no values. `.gitignore` covers `.env`, `secrets/`, model caches.
7. `CLAUDE.md` and `.claude/settings.json` (see E14). Have them in place before anyone starts using an assistant on the repo.
8. Local pre-commit hook running gitleaks, documented in the README (CI is the real gate; this just saves time).

## E2 · Compose deployment (Tue 24 Nov)

Build `deploy/docker-compose.yml` from the services table in `01-interfaces.md` §2.

- Networks: `public` (normal), `internal`, `llm-egress`, `web-egress` (all three `internal: true`). Only `web` publishes a port; Mailpit's UI is bound to `127.0.0.1`.
- `parser`: `network_mode: none`, shared volumes `parse-in` and `parse-out` with the ingestion worker, no secrets, `mem_limit`, `cpus`, `pids_limit`.
- Egress proxies: one small forward proxy image (for example Squid), pinned by digest, added to the inventory through the admission rule. `llm-proxy` allows `CONNECT` only to the provider's API host. `web-proxy` allows ports 80 and 443 and denies destinations in private, loopback, link-local, CGNAT and metadata ranges, as a second layer behind D's fetcher checks. Agents get `HTTPS_PROXY=http://llm-proxy:3128`; the fetcher gets `web-proxy`.
- Every service: non-root user, `read_only: true` with a small `tmpfs` where needed, `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`, healthcheck, image pinned by digest (`image: name@sha256:…`), `FROM` lines in Dockerfiles pinned by digest.
- Secrets as Docker secrets (files under `secrets/`, git-ignored, created by `make secrets` with random values): one database password per role, one `X-Service-Auth` secret per internal caller, the token-hashing pepper, the provider API key(s), the TOTP encryption key.

**Done when** `make up` starts every service healthy and `docker compose exec grading-agent curl https://example.com` fails while the same request to the provider host (once known) succeeds through the proxy.

## E4 · Identity (C27, C28)

`backend/identity/`:

- Passwords: Argon2id via `argon2-cffi` with the library's defaults; re-hash on login if parameters change.
- Sign-in limits: per account and per IP, fixed window (start with 5 failures per 15 minutes per account; record what you choose). Responses don't reveal whether the account exists.
- TOTP for instructors with `pyotp`. **This is a new dependency: run the admission check on it, paste the output in the PR, and keep that PR as the evidence that the rule was applied** (the brief asks to show it at least once). Secrets encrypted at rest with the key from Docker secrets.
- Sessions in the `sessions` table, cookie `HttpOnly; Secure; SameSite=Strict`, idle timeout 30 minutes for instructors (starting value).
- CSRF: double-submit token from `GET /api/auth/csrf`, required on all state-changing requests.
- `require_reauth(minutes=5)` dependency for release, publish, accept-key and decide-appeal routes; `POST /api/auth/reauth` takes a fresh TOTP code and sets `reauth_at`.
- Security headers middleware with the CSP in `01-interfaces.md` §10 (A checks it works with the built React app).

## E5 · Capability tokens and service identities (C32, R6)

`backend/identity/tokens.py`, used by the web app (mint, revoke) and the MCP server (verify):

```python
def mint(kind, *, subject_id=None, course_id, run_id=None, assignment_id=None,
         scopes: list[str], ttl: timedelta) -> str:
    raw = secrets.token_urlsafe(32)
    db.insert(CapabilityToken(token_sha256=sha256(pepper + raw), kind=kind, subject_id=subject_id,
                              course_id=course_id, run_id=run_id, assignment_id=assignment_id,
                              scopes=scopes, audience="mcp-server",
                              expires_at=now() + ttl))
    return raw

def verify(raw, *, audience) -> TokenContext | None:
    row = lookup(sha256(pepper + raw))
    if not row or row.audience != audience or row.revoked_at or row.expires_at < now(): return None
    if paused(row.course_id) or global_kill_switch(): return None
    return TokenContext.from_row(row)

def revoke_for(*, user_id=None, run_id=None, course_id=None): ...
```

- Scopes per kind are a fixed table in code (`SCOPES = {"student_delegate": [...], ...}`) matching `01-interfaces.md` §5, so nobody can mint a student token with `store_proposed_grade`.
- Revoke on logout (all delegate tokens of that user), at run end (C does this), on pause and on the kill switch.
- Only the hash is stored; raw tokens are never logged. Add a log filter that masks anything that looks like a token.
- Each service has its own database role (D), its own `X-Service-Auth` secret and, where the provider allows, its own model API key. Write the identity table for the report: user identities, agent identities, system identities, and what each can reach.

## E6 · Audit library (C11)

`backend/common/audit.py`, used by every service. One function, `append(row)`, which:

1. Redacts free text: every string argument longer than 64 characters becomes `{"len": n, "sha256": …}`.
2. In one transaction: `SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1 FOR UPDATE` (or a single-row `audit_head` table to lock on), computes `hash = sha256(prev_hash || canonical_json(row))`, inserts.

`scripts/verify_audit_chain.py` recomputes the chain and prints the first broken row. Run it in the nightly job and in the T-32 test (B).

## E7 · Admission check (C14, T-16)

`scripts/admission_check.py <pypi|npm> <name> [version]` prints PASS, REVIEW or FAIL with reasons:

1. **Exists:** query the registry's public JSON API (`https://pypi.org/pypi/<name>/json`, `https://registry.npmjs.org/<name>`). Not found → FAIL. This is what catches a hallucinated name.
2. **Intended package:** compare the name with a list of well-known packages in that ecosystem (keep a small list in `scripts/known_packages.txt`, including everything already in our lockfiles). Edit distance ≤ 2 from a known name that isn't itself → REVIEW ("did you mean …?"). Also show the summary and project URL so the person can confirm it's the thing they meant.
3. **Credible maintainer history:** first release date, number of releases, most recent release, number of maintainers, a linked source repository. Thresholds (start with: older than 90 days, at least 5 releases, source repository linked) → otherwise REVIEW.

Show it working twice for the report: once on `pyotp` (PASS), and once on a package name an AI assistant actually suggested that doesn't exist, if one comes up during the build. If none does, show it on a name you construct by misspelling a real package, and say that's what you did. Never publish a package to test this.

## E8 · CI pipeline, gates and SBOM (R9, R11, C14, C15, C16)

`.github/workflows/ci.yml`. Top-level `permissions: contents: read`; trigger on `pull_request` and `push` to `main`; never `pull_request_target`. Every `uses:` pinned to a full commit SHA with the version in a comment.

| Job | Runs | Fails the build when |
|---|---|---|
| `test` | `uv sync --frozen`, unit tests, `make verify` with `LLM_PROVIDER=fake`, MCP tool snapshot test, frontend `npm ci` and tests | any test fails |
| `pins` | `scripts/check_pins.py`: every `uses:` is a 40-hex SHA; every image and `FROM` has `@sha256:`; `uv.lock` and `package-lock.json` present and unchanged by `uv sync --frozen` / `npm ci` | anything unpinned |
| `deps` | OSV-Scanner over `uv.lock` and `package-lock.json`; `pip-audit`; `npm audit --audit-level=high` | a High or Critical finding not listed in `security/accepted-findings.yaml` with a justification and expiry date |
| `secrets` | gitleaks over the full history | any finding |
| `models` | `scripts/check_models.py`: only `.safetensors` under model directories; checksums match `aibom/models.lock`; ModelScan over the model directory | a pickle-based file, a checksum mismatch or a ModelScan finding |
| `admission` | on PRs that change a lockfile: lists new packages and checks the PR body contains admission-check output for each | a new package without it |
| `images` | build all images; Trivy image scan | a High or Critical vulnerability with a fix available, unless accepted as above |
| `sbom` | CycloneDX SBOM for the Python environment, for the npm lockfile and for each image; merge with `aibom/aibom.cdx.json`; upload as a build artifact | generation or merge fails |

**AI-BOM** (`aibom/aibom.cdx.json`, maintained by hand, reviewed in PRs): the embedding model (name, exact revision, file, SHA-256, licence, source), the hosted model(s) once known (provider, model snapshot IDs, as an external service), the datasets (seed generator and its seed, canary set, team-written course material, and the runtime sources: blog comments and fetched web pages, marked as not versioned), the MCP server (our own, with version and the hash of its tool list), the provider API endpoint. These are what scanners can't detect.

`make sbom` produces the same merged SBOM locally. `scripts/am_i_affected.py <name> [version-range]` searches the merged SBOM and prints every component that matches, with where it is used. That script is your answer to "are we affected?" in the drill.

## E9 · Limits and budgets (C10, T-25, T-26)

- Request size limit on the web app; upload size and type limits (D's route uses them).
- Rate limits: chat messages per student per minute and per day; uploads per user per hour; one active grading run per assignment.
- Budget: a `budgets` table per course per day in tokens or currency. C's adapter calls `budget.reserve()` before each model call and `settle()` after. Over budget → the call raises, the student gets a fixed message, an alert fires at 80% and at 100%.
- Set a hard spending cap on the provider account the day keys arrive. That is the last line if our own accounting has a bug.
- All numbers in `backend/common/settings.py` as starting values; record the final ones in the report.

## E10 · Kill switch and course pause (C30)

- Course pause: `POST /api/courses/{id}/pause` (instructor, re-auth) sets `course_controls.agents_paused`, revokes the course's agent tokens, and writes an audit row. Submissions still work. In-flight grading runs stop at their next model or tool call; C's harness sends the remaining submissions to the manual queue.
- Global kill switch for operators: `python scripts/kill_switch.py on --reason "…"` sets the global row, revokes every agent token, and makes the adapter and MCP server refuse every call. `off` reverses it.
- Test both during a running grading job (that's the C30 check from M1).

## E11 · Monitoring and alerts (R9, C11)

A `monitor` job runs every minute over new audit rows and writes to `alerts`, emails the ops address in Mailpit, and shows a banner on the instructor's audit screen (A). Rules, all with starting thresholds to tune:

| Rule | Fires when | Why |
|---|---|---|
| Denial spike | one agent gets more than N `E_SCOPE`, `E_AUTH` or `E_INVALID_ARGS` in 5 minutes | a fooled agent probing its limits |
| Answer-key overlap | any `answer_key_overlap` row | C23 hit |
| Validator rejections | more than N% of attempts in a run rejected | grader misbehaving or a bad prompt version |
| Full-marks rate | more than N% of a run's proposed grades flagged `full_marks` | mass injection or poisoned source |
| Fetcher blocked | any `non_public_address` block | SSRF attempt |
| Budget | 80% and 100% of a course's daily budget | T-25 |
| Tool list mismatch | an agent refused to start on the MCP hash check | T-18 |
| Chain broken | `verify_audit_chain.py` fails | log tampering |
| Kill switch or pause | any change | operators must know |

## E12 · Supply-chain remediation (Part B)

1. Run every scanner on the first full build. Put **every** finding, including ones from the M1 Part A assessment, in `docs/remediation-log.md` using the Appendix D columns: finding, source, severity, decision (upgrade, replace, pin, isolate, remove, accept), change (commit or PR), verification (clean re-scan or passing test).
2. Fix what you can with real commits. Keep the scan output from before and after one fix for the demo (a screenshot or the saved report).
3. Accepting a finding needs a justification under the Appendix C rules and goes in `security/accepted-findings.yaml` with an expiry date.
4. Update the M1 inventory: every row from "Proposed" to the actual pinned version and integrity evidence; add the npm packages (React, Vite, TypeScript and whatever A admits), `pyotp`, the proxy image, and remove anything we didn't use. The model rows change once the provider is known.

## E14 · AI-assisted development policy and runbook

**`CLAUDE.md`** (rules for the coding assistant):

- Never read, print or write `.env`, `secrets/` or any credential. Never put secrets in code or tests.
- Never add a dependency without running `scripts/admission_check.py` and showing the output.
- Never edit `uv.lock` or `package-lock.json` by hand; use `uv add` / `npm install --save-exact`.
- Use synthetic data only; never real names or emails.
- Injection tests use `CANARY-` strings only.
- Don't change `prompts/`, `backend/mcp_server/descriptions.py` or CI workflows unless the task is about them, and say so in the PR.

**`.claude/settings.json`** with deny rules for reading secrets and for network commands, for example:

```json
{
  "permissions": {
    "deny": ["Read(./.env)", "Read(./.env.*)", "Read(./secrets/**)",
             "Bash(curl:*)", "Bash(wget:*)", "Bash(git push:*)"]
  }
}
```

Check the exact rule syntax against the assistant's current documentation before relying on it, and test that a denied read is actually refused.

**Report §5** covers: which assistants and extensions each member used (inventory row SC-51), what each could read, write and execute, the rules files above and how they were reviewed, the PR template and CODEOWNERS review gate, and the CI gates.

**Runbook (`docs/runbook.md`, one page):** detect (which alerts, who receives them), triage (how to read the audit log for one agent, one course, one run), contain (pause the course or use the kill switch; revoke tokens; rotate the affected key), recover (manual queue, re-run grading after the fix, verify the audit chain), communicate (who tells the instructor and students, with a short template), and after the incident (remediation log entry, threat-model update).

## E16 · Advisory drill (Part C)

Before Week 13, run a practice drill: pick one component from our SBOM (a package version, the embedding model revision, a base image), pretend it's compromised, and time yourself answering the five questions with `am_i_affected.py`. Write the note in the two-page format so the real one is mostly filling in. For the real drill:

1. **Exposure:** run `am_i_affected.py` against the SBOM of the deployed commit; paste the output.
2. **Blast radius:** which service uses it, that service's network, database role, secrets and tokens (from the identity table in E5).
3. **Remediation:** the commits.
4. **Verification:** clean re-scan, new SBOM without the component, tests green.
5. **Communication:** a short message for instructors and operators.

Record the time from receiving the advisory to answering question 1. If we're not affected, the note still shows how we established that and how long it took.

## E13 · Your verification tests

| Test file | Threat | Canary or input | Controls | Expected |
|---|---|---|---|---|
| `test_T15_parser_isolation.py` | T-15 | Inside the `parser` container: try to open a socket to `db:5432` and to a public address; list environment variables | C14 | Both connections fail; no secret in the environment |
| `test_T16_slopsquat.py` | T-16 | `admission_check.py pypi <nonexistent name>` | C14 | FAIL: does not exist |
| `test_T17_unpinned_ci.py` | T-17 | Fixture workflow with `uses: actions/checkout@v4` and an image without a digest | C16 | `check_pins.py` fails on both |
| `test_T19_leaked_credential.py` | T-19 | Fixture file with a fake key in a known secret format marked `CANARY-T19`; separately, connect as `rubrica_ingest` and read `submissions` | C16, C12, C31 | gitleaks reports the fixture; the ingest role is denied |
| `test_T25_chat_flood.py` | T-25 | Chat messages above the per-minute limit; a course with its budget nearly spent | C10, C30 | 429 after the limit; fixed message when the budget is spent; alert at 80% |
| `test_T26_upload_flood.py` | T-26 | Oversized file; uploads above the hourly limit; a second grading run on the same assignment | C10 | rejected before parsing; 429; second run refused |
| `test_T28_account_takeover.py` | T-28 | Repeated wrong passwords; instructor login without TOTP | C27 | locked out after the limit; instructor endpoints refused until TOTP |
| `test_T30_model_file.py` | T-30 | A `.pkl` file placed in the model directory | C15 | `check_models.py` fails; the loader refuses |
| `test_T31_stale_session.py` | T-31 | Approve a release with a session whose re-auth is older than the window | C28 | `401 reauth_required`; nothing released |

Plus the C30 test (pause during a run) with C, and the C32 token tests with B.

## Questions you should be ready for

- If the grading agent's model API key leaked, what could an attacker do with it, and what couldn't they do?
- How do you know the SBOM includes the embedding model, and how would you know if someone swapped it?
- What happens, step by step, when you flip the kill switch during a grading run?
- How did you review code written by an AI assistant?
