# Person B · Security Architect

You keep the design and the code consistent with each other, and you prove it. You own the verification framework every other member writes tests in, the authorization and row-level-security tests that cut across everyone's code, the threat-model revision, the revised DFDs, the completed traceability matrix, and the final report as editor. Three rubric areas lean on your work directly: verification (15), threat revision and traceability (10), and a large part of controls (20), because "least privilege enforced in code and configuration, not just in prompts" is what your tests show.

Read `README.md` and `01-interfaces.md` first. Section 11 of `01-interfaces.md` (test format) is yours.

## What you own

| Kind | Items |
|---|---|
| Controls you verify directly | C29 object-level checks on every route, C31 row-level security (D builds it), C32 token rules (E builds them), C11 audit evidence (T-32), C04 upload metadata (T-14) |
| Verification tests | T-14, T-23, T-27, T-32, the route authorization matrix, the RLS suite, the token-scope suite. You also review every other test for traceability |
| Threat model | Revised DFDs, new and re-rated threats, the "what changed and why" table, the completed traceability matrix |
| Report | Editor of the whole report (30 pages maximum excluding appendices); author of §1 threat-model revision, §2 control implementation (assembled from owners' rows), §3 verification evidence |
| Demo | You own the control demos (steps 4 to 7 of the demo plan); C and A present parts of them |

## Timeline

| ID | Task | Due | Depends on |
|---|---|---|---|
| B1 | Verification framework, fixtures and report generator | **Tue 24 Nov** | E: repo |
| B2 | Test-writing guide for the team (in `tests/verification/README.md`) | Tue 24 Nov | B1 |
| B3 | Route authorization matrix test | Fri 27 Nov (skeleton routes) · grows to Thu 3 Dec | routes exist |
| B4 | RLS test suite | Fri 27 Nov | D1 |
| B5 | Token-scope test suite | Fri 27 Nov | E5, C2 |
| B6 | T-14, T-23, T-27, T-32 tests | Wed 2 Dec | D6, E6 |
| B7 | Threat-model revision and revised DFDs | draft Wed 2 Dec · final Mon 7 Dec | the build |
| B8 | Coverage check: every Critical and High threat has a passing test | **Fri 4 Dec** | everyone |
| B9 | Traceability matrix completed | Mon 7 Dec | B8, live runs |
| B10 | Report assembly and consistency pass | Tue 8 Dec | all sections |
| B11 | Demo rehearsal of the control demos | Tue 8 Dec | A, C |

---

## B1 · Verification framework

**Why.** The brief asks for one test per Critical and High threat, each stating the threat ID, canary, control, expected and observed behaviour, runnable with one command, with probabilistic tests run repeatedly and reported as a fraction. If each member invents their own format, assembling §3 and the matrix becomes a week of copying. One decorator and one report generator make the evidence fall out of the test run.

**Files.**

```
tests/verification/
  README.md            # B2: how to write a test (rules below)
  conftest.py          # fixtures
  framework.py         # @verification, registry, result capture
  test_T01_*.py … test_T36_*.py
scripts/verify_report.py   # turns results.json into report.md and matrix_rows.csv
```

**`framework.py`.**

```python
REGISTRY: list[dict] = []

def verification(*, threat, control, location, canary, expected, kind="deterministic", runs=1):
    def deco(fn):
        meta = dict(threat=threat, control=control, location=location, canary=canary,
                    expected=expected, kind=kind, runs=runs,
                    test=f"{fn.__module__}::{fn.__name__}")
        REGISTRY.append(meta)
        marker = pytest.mark.probabilistic if kind == "probabilistic" else pytest.mark.deterministic
        return marker(pytest.mark.verification(**meta)(fn))
    return deco
```

A pytest plugin hook (`pytest_runtest_makereport`) records, for each verification test: pass or fail, the `observed` string the test sets (`request.node.observed = "..."`), and the audit-log rows it collected. For probabilistic tests, `make verify-live RUNS=N` runs each one N times (`pytest --count=N` via `pytest-repeat`, which goes through the admission check, or a simple loop in the runner) and records `passed/N`.

**Fixtures in `conftest.py`.**

- `seeded_db`: a fresh database from migrations plus `make seed CANARIES=1`, rolled back or recreated per test module.
- `fake_llm(script_name)`: installs `FakeLLM` with a script and returns the recorder (C provides FakeLLM).
- `as_student(course)`, `as_other_student(course)`, `as_instructor(course)`, `as_other_instructor`, `anonymous`: API clients with real sessions, including TOTP and CSRF.
- `agent_token(kind, …)`: mints a capability token through E's library.
- `audit_rows(since=…, action=…, decision=…)`: reads the audit log for assertions.
- `mailpit`: reads messages from Mailpit's API.
- `live_only`: skips unless `LLM_PROVIDER` is a real provider.

**`scripts/verify_report.py`** writes:

- `docs/verification/report.md`: one row per test: test ID, threat, control(s), canary, expected, observed, result (pass/fail or `k/N`), the provider, model and prompt version for live runs, and the date.
- `docs/verification/matrix_rows.csv`: threat, control, implementation location (the `location=` field the owner fills in the decorator, e.g. `backend/mcp_server/tools.py:store_proposed_grade`), test ID, result. You paste or import this into the matrix.

## B2 · The rules every test follows (write these into `tests/verification/README.md`)

1. **One threat per file**, named `test_T<nn>_<what>.py`. A threat can have several tests.
2. **Canaries only.** Every injected string contains `CANARY-T<nn>-<4 hex>` and asks for something harmless: a marker string, a call to a logging tool, a score change on synthetic data.
3. **Structural and deterministic controls are tested with the model fully fooled.** Script FakeLLM to do exactly what the canary asks, then assert the control still holds. A test that passes only because the model ignored the canary proves nothing about the control.
4. **Model-level controls are also measured live.** Mark them `kind="probabilistic"`, run them N times on the real model, and report the fraction. In the `expected` text, name the deterministic control that limits the damage when the model gets it wrong.
5. **Assert on evidence, not on absence of errors.** Check the database state, the audit rows, the orchestrator transcript, the Mailpit message.
6. **Set `observed`** to a one-line description of what actually happened, so the report reads correctly when a test fails.
7. **No network outside the Compose stack** in deterministic tests; they run in CI on every push.

## B3 · Route authorization matrix (C29, T-27)

**Why.** Object-level authorization fails one route at a time: the route someone added late on a Wednesday without `require_course_member`. A test that enumerates every route and demands an expectation for each turns "we check every route" from a claim into a CI gate.

`tests/authz/test_route_matrix.py`:

1. Import the FastAPI app and list every route (`app.routes`), method and path.
2. Load `tests/authz/expectations.yaml`, which says for each route and each actor (`anonymous`, `student_same_course`, `student_other_course`, `instructor_same_course`, `instructor_other_course`) whether the request is allowed and what status a denied one returns (`401`, `403`, or `404` where we hide existence).
3. Fail if any route is missing from the YAML. That is the forcing function.
4. For each route and actor, call it with the seeded IDs and assert the expected status. For allowed reads, also assert the response contains only the caller's own data where that applies.

**T-27 test** (`test_T27_unpublished_access.py`): a student requests an unpublished assignment and an answer key by ID through every route that could return them → `404`, no content, denial in the audit log.

## B4 · Row-level-security suite (C31, T-23)

`tests/authz/test_rls.py`, connecting directly to PostgreSQL as each runtime role with the RLS settings applied:

- `rubrica_mcp` as student A: `SELECT * FROM proposed_grades` without any `WHERE` returns only A's released grades. This is the T-23 test: it simulates the code bug (a missing ownership filter) and shows the database still holds.
- `rubrica_mcp` as student: `answer_keys` returns zero rows.
- `rubrica_mcp`: `UPDATE proposed_grades SET status='released'` is denied.
- `rubrica_grading` for run R: can't read submissions of another assignment; can't read `blog_chunks`.
- `rubrica_ingest`: can't read `submissions` or `proposed_grades`.
- Every role: `UPDATE` and `DELETE` on `audit_log` denied.
- A session with no RLS settings set returns nothing from protected tables (fail closed).

`test_T23_missing_filter.py` wraps the first case in the `@verification` format.

## B5 · Token-scope suite (C32)

`tests/authz/test_tokens.py` against the MCP server:

- Expired token → `E_AUTH`. Revoked token (after logout, after run end, after pause) → `E_AUTH`.
- Token with another audience → `E_AUTH`.
- Student token calling `store_proposed_grade`, `propose_grade_change` or `list_appeals` → `E_SCOPE`.
- Grading-run token used for another run's result IDs → `E_NOT_FOUND`.
- Token never appears in a model's context: search every FakeLLM recorder entry from a full workflow for the token prefix.
- Token never appears in logs: grep the captured service logs.

## B6 · Your other threat tests

| Test | Threat | Canary or input | Controls | Expected |
|---|---|---|---|---|
| `test_T14_upload_metadata.py` | T-14 | Student uploads a file with form fields `kind=answer_key`, `role=instructor`, `course_id=<other course>` and a filename containing `CANARY-T14-answer-key` | C04, C29 | Stored record has the student as uploader, the route's course, `source_kind` set by the server, status `pending`; nothing reaches `answer_keys` |
| `test_T23_missing_filter.py` | T-23 | Query without an ownership filter, as in B4 | C31, C03, C21 | Only the caller's rows |
| `test_T27_unpublished_access.py` | T-27 | As in B3 | C29, C03 | `404`, audited |
| `test_T32_audit_evidence.py` | T-32 | Full appeal flow: student appeal → agent proposal → instructor decision | C11 | Audit rows exist for each step with actor, on-behalf-of, approver, before and after values; `verify_audit_chain.py` passes; then, connected as the migration owner in the test, alter one row → the verifier reports that row |

## B7 · Threat-model revision (report §1)

**What changed and why.** Keep a running table in `docs/threat-model/changes.md` from today: date, change, reason, who found it. Things already known:

- C31–C37 and the structured rubric (README §1), with the reason for each.
- `grade_submission` and `check_citations` are local tools; M1 §2.2 said otherwise.
- Citations are extracted by code, not by the grader (`01-interfaces.md` §7). This shrinks T-07 and T-08's attack path: no model decides which address is fetched.
- The release email carries no model text, which removes most of T-11 and T-33 by design.
- The parser runs in a container with no network (T-15's blast radius).
- The React front end adds an npm supply chain and moves part of C07 into the browser.
- Egress proxies and the job queue are new components.

**New threats.** The brief asks you to bring in Weeks 11 to 15: coding-agent and CI threats, deployment and runtime threats, and the Week 14 isolation patterns. Go through those slides and the build itself, and add threats from T-38 onward, rated on the same scales. Candidates to examine (check each against the lectures before adding it):

- A coding assistant reads a secret or is steered by text in the repository (a README or issue containing instructions) into adding a dependency or weakening a check.
- A CI job with write permissions runs code from a pull request.
- A secret leaks through container environment variables or logs.
- The egress proxy is misconfigured and an agent reaches the internet directly.
- The job queue lets one course's grading run starve another's (availability).
- A long chat conversation pushes the system prompt out of the effective context.

**Re-rating.** For each M1 threat, decide whether the implemented controls change its likelihood. Re-rate only with a reason you can point to in code or a test result. Keep the M1 rating next to the new one.

**Revised DFDs** (`docs/threat-model/`): update Level 0, 1 and 2 to show the egress proxies, the isolated parser, the job queue, the release service's writes, the audit view reading D6, the manual-grading screen reading D11, the assembler's direct search (C35), `list_appeals`, and the React app as the browser view. Add the build-pipeline diagram for TB-12 that M1 promised. The colour legend should say "who can edit the data going into this component", as the team agreed.

## B8 · Coverage check (Fri 4 Dec)

Write `scripts/check_coverage.py`: read the threat register (export it to `docs/threat-model/threats.csv`) and the verification registry; fail if any Critical or High threat (T-01 to T-29) has no test, or if a test names a threat or control that doesn't exist. Run it in CI from Fri 4 Dec. Ownership is in `README.md`; chase owners from Wed 2 Dec.

## B9 · Traceability matrix (Appendix A)

Complete every row: one row per control per threat. The M2 columns are implementation location, verification test, result, and residual risk. Take location and result from `matrix_rows.csv`; take residual risk from the owner (one sentence, specific). Add rows for C31–C37 and for new threats. Every Critical and High threat must have at least one complete row. The matrix must agree with the code: spot-check ten locations by opening the file.

## B10 · Report assembly

- Template with the nine sections and a page budget. Starting budget, adjust as drafts come in: §1 4 pages, §2 6, §3 5, §4 3, §5 2, §6 3, §7 3, §8 2, §9 2.
- Owners deliver drafts by Mon 7 Dec (README §3 has who writes what).
- Your consistency pass: every threat, control and test ID mentioned exists; numbers in §3 come from `report.md`, not from memory; every deviation from M1 in §2 also appears in §1; no section claims a control the matrix doesn't show.
- The appendices hold the matrix, the full verification report, the remediation log and the system card.

## Questions you should be ready for

- Pick any Critical threat: which test proves its control, and what did the test observe?
- Which controls are model-level, and what limits the damage when they fail?
- What changed in the threat model since M1, and what made you change it?
- How do you know there's no API route without an authorization check?
