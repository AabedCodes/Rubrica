# Threat model: what changed since Milestone 1, and why

Owner: B. A running log, newest first, started 28 Nov 2026 (B7). It feeds report §1. Add a row the same day you notice something: a design change, a new threat, a re-rating with its evidence, or a gap a test found. Re-rate a threat only with a reason you can point to in code or a test result, and keep the M1 rating next to the new one.

## Gaps found by tests

| Date | ID | What | Found by | Affects | Owner | Status |
|---|---|---|---|---|---|---|
| 2026-11-28 | FINDING-B4-01 | `rubrica_mcp` RLS policies limit rows to the token's course (`course_id = rubrica.course_id`) but don't check that the user is **enrolled** in that course. With a token naming the wrong course, an instructor of course 1 can read course 2's submissions and proposed grades; a student can read course 2's published assignments. The `_member()` helper in migration 0003 exists but isn't used for these policies. Token minting is then the only check, which goes against C31's "re-check rights at the resource" | `tests/authz/test_rls.py` (2 strict-xfail tests) | T-05, T-23 (C31, C21); widens the blast radius of any E5 minting bug | D | open |
| 2026-11-28 | FINDING-E-CI-01 | D1's 13 database tests and every RLS check skipped in CI (no PostgreSQL in CI), so C31 had no CI evidence | B4 review | C31 evidence (§3) | B, E | fixed: `db-tests` job (PostgreSQL service container) |
| 2026-11-27 | FINDING-E-CI-02 | Frontend tests, lint and build never ran in CI | review of PR #17 | C07, C14 evidence | E | fixed in PR #22 (`frontend` job) |
| 2026-11-22 | FINDING-E2-01/02 | `web` and then (on Docker Desktop) `web` and Mailpit had an outbound route | `compose-smoke`, local `make up` | T-19, T-08 blast radius | E | fixed: edge proxy (PR #8); residual: edge egress on Docker Desktop only |

## Design changes since M1 (from `docs/plan/README.md` §1)

| Change | Why | Threats affected | Where |
|---|---|---|---|
| C31: RLS plus one DB role per service | MCP server's role could read every course; re-check rights at the resource | T-05, T-23 | `backend/db/migrations/versions/0002_roles.py`, `0003_row_security.py` |
| C32: agent tokens bound to the MCP server, short-lived, never forwarded, revoked at logout/run end | M1 never fixed token rules | T-05, T-21 | `backend/identity/tokens.py` (E5, not built yet) |
| C33: MCP returns fixed error codes, never echoes request text | error text is an injection channel back into a model | T-02, T-03 | `backend/mcp_server/` (C2) |
| C34: `store_proposed_grade` takes a checked result ID, never a score | the orchestrator could otherwise store any in-range score | T-04 | C2 |
| C35: course-material search for grading moves into the context assembler; orchestrator never sees excerpts | planner–executor rule: planner never reads untrusted text; closes part of T-03 | T-03, T-04 | C4 |
| C36: review screen shows exactly the text the grader read, flags full marks/outliers/disagreement | hidden text visible; fights confirmation fatigue | T-04, T-37 | `frontend/src/pages/assignments/ReviewDetailPage.tsx` (PR #17) |
| C37: instructor agent gets `list_appeals`; audit and manual-queue screens | closes M1 gaps (no tool fetched appeals; D6, D11 never read) | T-02, T-32 | C, A |
| `grade_submission`, `check_citations` are local tools in the grading agent | matches the Level 1 diagram; fixes M1 report §2.2 | — | C |
| Cited URLs extracted by code, not by the grader | no model decides which address the fetcher visits | T-07, T-08 (shrinks) | `backend/fetcher/url_policy.py` (D8) |
| Release email carries no model-written text | removes injected-link and header paths by design | T-11, T-33 (shrinks) | `backend/sinks/grade_email.py` (D3) |
| Parser in a container with no network and no credentials | a malicious parser library has nothing to steal | T-15 (blast radius) | `deploy/docker-compose.yml` `parser`; `scripts/egress_smoke.sh` |
| React SPA | adds an npm supply chain; moves part of C07 into the browser | T-10, T-16 | `frontend/`, `.npmrc`, ESLint HTML-sink rule (A3) |
| Egress proxies (`llm-proxy`, `web-proxy`) and the edge proxy | agents reach only the provider; fetcher only the public web; published ports on a no-secret container | T-08, T-19 | `deploy/proxy/` |
| Job queue (`jobs` table) | grading, ingestion and indexing run as background jobs | availability (candidate new threat) | D |

## Candidate new threats (T-38 onward), to check against the Week 11–15 lectures

| Candidate | Seen in our build | Next step |
|---|---|---|
| Coding assistant reads a secret or is steered by repo text into weakening a check | 22 Nov: an assistant session started outside the repo didn't load the deny rules (remediation log row 3) | rate; control = `CLAUDE.md`, deny rules, review gate, CI |
| CI job with write permissions runs PR code | all workflows are `contents: read` or `issues: write`; no `pull_request_target` | rate low; cite `ci.yml`, `role-claims.yml` |
| Secret leaks through container env vars or logs | secrets are Docker secret files, not env; parser env checked by `egress_smoke.sh` | rate; add a log-masking test with E5 |
| Egress proxy misconfigured, agent reaches the internet directly | `egress_smoke.sh` checks every service on every PR | rate low; residual on Docker Desktop |
| One course's grading run starves another's (job queue) | not tested yet | rate; needs D's queue limits |
| Long chat pushes the system prompt out of effective context | not tested yet | rate; C's chat agent |
| **Token minted for the wrong course is honoured by the database** | FINDING-B4-01 | likely a re-rating of T-05/T-23 rather than a new threat; decide once D responds |
