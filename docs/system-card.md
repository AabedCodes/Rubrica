# Rubrica system card

**Status: draft (A10), 2026-11-27.** Owner: A. For engineers and operators; target length 2–4 pages (brief, Appendix B).

Every component and control below carries a status:
- **Built:** merged on `main`.
- **In review:** in an open pull request.
- **Planned:** designed in [`01-interfaces.md`](../01-interfaces.md) and [`docs/plan/`](plan/README.md), not built yet.

Nothing marked *planned* should be read as working today. Facts that must come from an owner are marked `TODO(<owner>)`; figures appear only once a script or test has produced them.

---

## 1. System overview

Rubrica is an agent-assisted grading system for one university course setting.

- **Purpose.** Help an instructor grade written assignments faster without giving up control of the grade. AI agents propose grades, answer students' questions about course material, and draft assignments and grade changes. A human approves everything that affects a student's record.
- **Users.**
  - Instructors create assignments, rubrics and answer keys, review and approve grades, and decide appeals.
  - Students submit work, see released grades and feedback, ask questions, and appeal.
- **Deployment.** A local Docker Compose stack on a member's laptop (services and networks: [`01-interfaces.md`](../01-interfaces.md) §2). Synthetic data only. Email goes to Mailpit, never to a real mail server.
- **State today.** The data layer, ingestion, retrieval, fetcher, platform and the front end's shell and walking-skeleton screens are built; the review screen is in review. Identity, the model adapter, the agents, the MCP server and the release service are planned. Python services run a placeholder entry point until their owners replace it.

## 2. Models and components

| Component | Status | Detail |
|---|---|---|
| Embedding model `BAAI/bge-small-en-v1.5` | Built | Runs locally; revision pinned in [`aibom/models.lock`](../aibom/models.lock) (`5c38ec7c…`, MIT licence) |
| Model provider and model snapshots for the orchestrator, grader, checker, chat and instructor roles | Planned | `TODO(C)`: provider chosen when keys arrive (R7). Until then all calls go to a scripted fake model |
| Provider-neutral model adapter with `FakeLLM` (C1) | Planned | `backend/llm/`; no other module may import a provider SDK |
| Database: PostgreSQL 18 with pgvector, schema, one role per service, row-level security (D1, C31) | Built | [`backend/db/`](../backend/db/README.md) |
| Ingestion with an isolated parser (D4) | Built | `parser` service has `network_mode: none` and no credentials |
| Course-scoped retrieval (D5), blog indexing (D7) | Built | [`backend/retrieval/`](../backend/retrieval/search.py), [`backend/ingestion/`](../backend/ingestion/README.md) |
| Sandboxed citation fetcher (D8) | Built | [`backend/fetcher/`](../backend/fetcher/README.md), behind `web-proxy` |
| React front end: shell, safe rendering, walking-skeleton screens (A1–A3) | Built | Merged in #14–#16; runs against a mock API until the backend routes exist |
| React front end: review screen (A5) | In review | PR #17 |
| Third-party packages | Built (process) | Every package passes [`scripts/admission_check.py`](../scripts/admission_check.py); `backend/uv.lock` is hash-locked; images and actions are pinned ([`scripts/check_pins.py`](../scripts/check_pins.py)). Versions: `TODO(E)`, from the SBOM (E8, planned) |

## 3. Capabilities and authority

### What each agent will be able to do (all planned)

From [`01-interfaces.md`](../01-interfaces.md) §5. **No agent is built yet.**

| Agent | Acts for | Tools | Can change |
|---|---|---|---|
| Grading orchestrator (2.1) | one grading run | `list_run_submissions`, `store_proposed_grade`, `send_to_manual_queue`; local `grade_submission`, `check_citations` | inserts **pending** proposed grades and manual-queue rows only |
| Quarantined grader (2.3), evidence checker (2.6) | — | **none**: the adapter refuses tools for these roles | nothing; their output is validated by code |
| Chat agent (3) | one signed-in student | `search_course_material`, `get_my_feedback`, `open_appeal` | inserts an appeal for that student only |
| Instructor agent (4) | one signed-in instructor | `get_assignment`, `list_appeals`, `draft_assignment`, `draft_answer_key`, `propose_grade_change` | inserts drafts and **pending** proposals only |

By design, **no tool releases a grade, publishes anything, sends email, changes a released grade, or reads answer keys for students.** Agents are to receive short-lived capability tokens bound to the MCP server and one course, never a user's session (C21, C32; planned).

### Actions that need human approval (R10)

| Action | Who approves | Why the line is here | Status |
|---|---|---|---|
| Releasing grades | Instructor, after re-entering a TOTP code within 5 minutes (C28) | A released grade is what a student acts on, and the grader reads untrusted text, so its score is only a proposal | Screens built (A2) and in review (A5, #17); re-auth and release service planned (E4, D3) |
| Publishing an assignment | Instructor, re-auth | Students see the rubric, whose maximums bound every score (C02) | Screen built (A2); route planned (D6) |
| Accepting an answer key | Instructor, re-auth | The key decides objective marks (C20) and must never reach students (T-01) | Route proposed in #18; planned |
| Deciding an appeal or grade-change proposal | Instructor, re-auth, on a screen showing database values (C25) | The appeal is written by the student and the rationale by an AI; neither may change a grade alone (T-02) | Planned (A7, C7) |
| Publishing uploaded course material | Instructor, after reading the extracted text (C04) | Approved material becomes searchable, so it is a path for injected text (T-03) | Planned (A6, D6) |

## 4. Data

- **Stored** in PostgreSQL inside the stack (tables in [`01-interfaces.md`](../01-interfaces.md) §3.1). Row-level security is enabled and forced on the course-scoped tables. Retention: `TODO(D)`.
- **Read by agents (planned):**
  - Submissions, by the grader only, wrapped as untrusted.
  - Course material and blog content, through retrieval. The grader never searches the blog (C24).
  - Cited web pages, fetched by the sandboxed fetcher at addresses chosen by code, not a model (built; T-07, T-08).
- **Sent to the model provider (planned):** prompts built from rubric, key, submission and material excerpts; chat messages; instructor-agent requests. The provider's retention and training use: `TODO(C)`, from R7.
- **Seed data provenance:** [`docs/seed-data.md`](seed-data.md).
  - Faker names under `example.edu`, with a fixed seed.
  - Team-written course material.
  - A team-written chapter standing in for a third-party source.
  - Answer keys marked with `KEYMARK` strings.
  - Harmless canaries in `seed/canaries/`.

## 5. Intended use and out-of-scope use

**Intended:** a course team grading written assignments against structured rubrics, with an instructor reviewing every proposed grade before release.

**Out of scope:**
- High-stakes exams without human grading.
- Scanned or handwritten work (the parser extracts text, not images).
- Releasing grades without review.
- Real student data.
- Any course whose instructor can't review the volume of proposed grades.

## 6. Known limitations and failure modes

| Limitation | What it means | Measured |
|---|---|---|
| A believable but wrong score inside the rubric's range (T-37, the accepted risk) | Range checks can't catch a plausible wrong score; human review is the control | BO2 agreement `TODO(A9)` from the blind sample (A4) |
| A grader fooled by hidden instructions (in-range part of T-04) | Isolation and the validator bound the damage but can't prevent a high in-range score | `TODO(B)`: T-04 pass fraction |
| A paraphrased answer key in chat | The planned C23 check catches overlap, not paraphrase | `TODO(B/C)` |
| Hidden text that extraction drops | The review screen shows what the grader read, not everything in the original file | not measured |

## 7. Security controls summary

| Defence | Where | Main threats | Status |
|---|---|---|---|
| Isolated networks; egress only through allow-listed proxies; non-root, read-only containers; images pinned by digest | `deploy/` (E2) | T-07, T-08, T-15 | Built |
| Parser in a container with no network and no credentials | `parser` service (D4) | T-15 | Built |
| Sandboxed fetcher: code-chosen URLs, scheme, port and address checks, size and redirect limits, behind `web-proxy` (C06) | `backend/fetcher/` (D8) | T-07, T-08 | Built |
| One database role per service and row-level security (C31) | `backend/db/` (D1) | T-05, T-23 | Built |
| `audit_log` table: every role may insert, none may update or delete | `backend/db/` (D1) | supports investigation (R9) | Built (table and grants); hash-chain writer and verifier planned (C, E) |
| Server-side Markdown filter that strips images and raw HTML (C07, layer 1) | `backend/sinks/text_policy.py` (D9) | T-09, T-10 | Built |
| Release email with fixed text and no model-written content | `backend/sinks/grade_email.py` (D9) | T-11, T-33 | Built (template); release service planned (D3) |
| Package admission check; pinned actions and images; hash-locked Python lockfile (C14) | `scripts/`, CI (E3, E7) | T-16, T-19 | Built |
| Browser rendering of model text via `SafeMarkdown`; lint rule bans HTML sinks; CSP (C07, layers 2–3) | `frontend/` (A3), `01-interfaces.md` §10 | T-09, T-10 | Built (A3, #15); CSP header set by `web`, planned |
| npm hardening: install scripts off, exact pins (C14) | `frontend/.npmrc` (A1) | T-16 | Built (A1, #14) |
| Review screen showing the text the grader read, with invisible characters marked; flagged grades not bulk-approvable (C36) | `frontend/` (A2, A5) | T-04, T-37 | Built (review list, A2); review screen in review (A5, #17) |
| Dual-LLM isolation: the orchestrator never reads untrusted text; grader and checker have no tools (R8, C35) | `backend/agents/grading/` (C4, C5) | T-03, T-04 | Planned |
| Output validator: schema, maximums, 0.5 steps, quotes checked, totals computed by code (C02) | grading agent (C5) | T-04, T-37 | Planned |
| Objective criteria marked by code (C20) | grading agent (C5) | T-04 | Planned |
| Capability tokens and scopes, fixed MCP error codes, `store_proposed_grade` takes result IDs (C21, C32–C34) | `backend/mcp_server/`, `backend/identity/` (C3, E5) | T-05 | Planned |
| Sign-in with TOTP for instructors; re-auth for approvals (C27, C28) | `backend/identity/` (E4) | T-02, T-05 | Planned (sign-in and re-auth screens built, A1) |
| Course pause and global kill switch (C30) | E10 | runaway or compromised agents | Planned |
| Alerts over the audit log (C11) | E11 | probing, key overlap, mass full marks | Planned |
| SBOM and AI-BOM in CI (R11) | E8 | supply-chain response | Planned (AI-BOM model entry built) |

## 8. Monitoring and incident response

Planned (E11, E14):
- A monitor job over new audit rows that raises alerts, emails the ops address in Mailpit and shows a banner on the instructor's audit view.
- A runbook covering pausing a course, the kill switch, rotating secrets and answering an advisory.

Thresholds and the runbook link: `TODO(E)`.

## 9. Reporting issues

See [`docs/disclosure.md`](disclosure.md).

## 10. Change log

| Date | Change | By |
|---|---|---|
| 2026-11-27 | First draft, with built, in-review and planned status from `main` at `cfaa661` (after #14–#16 merged) | A |
