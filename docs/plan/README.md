# Rubrica · Milestone 2 task plan

This folder holds the Milestone 2 task assignments for the team. Read this file first, then `01-interfaces.md`, then the file for your role. Everything here builds on the Milestone 1 design: the report, the threat sheet (threats T-01 to T-37, controls C01 to C30) and the diagrams. Where this plan changes the M1 design, it says so.

| File | Who reads it |
|---|---|
| `README.md` | Everyone: decisions, timeline, ownership, deliverables |
| `01-interfaces.md` | Everyone: the shared contracts (repo layout, database, tokens, MCP tools, model adapter, audit log, API, test format). Change it only by PR, reviewed by the owner named in each section |
| `A-product-owner.md` | Person A |
| `B-security-architect.md` | Person B |
| `C-agent-llm-engineer.md` | Person C |
| `D-data-retrieval-engineer.md` | Person D |
| `E-platform-devsecops-engineer.md` | Person E |

## 1. Decisions this plan is built on

| Decision | Choice | Consequence |
|---|---|---|
| Optional features | Build both the course blog and web-page checking | Threats T-06, T-07, T-08, T-13, T-20 and T-21 stay in scope and need verification tests |
| Model provider (R7) | Not chosen yet; the team will receive API keys from a frontier-model provider | All model calls go through one provider-neutral adapter. Until keys arrive, everything runs on a scripted fake model. When keys arrive, one person (C) adds that provider's adapter in about a day, and C documents the provider's data handling for R7 |
| Front end | React single-page app (Vite + TypeScript) | Adds an npm supply chain (lockfile, `npm audit`, install scripts off) and moves output rendering (C07) partly into React |
| Starting point | New repository | Person E creates it on day one; the layout is fixed in `01-interfaces.md` |
| Stack | Python 3.13, FastAPI, PostgreSQL 18 with pgvector, local embedding model `BAAI/bge-small-en-v1.5`, MCP Python SDK, Docker Compose, Mailpit, GitHub Actions | As proposed in the M1 supply-chain inventory; every new package goes through the admission rule |

### Changes to the M1 design (all of them get recorded in the M2 threat-model revision)

These came out of reviewing the design against the Week 8 and Week 9 lectures after the M1 presentation.

| New ID | Change | Why | Owner |
|---|---|---|---|
| C31 | Row-level security in PostgreSQL plus one database role per service | The MCP server's role could read every course; the lecture's rule is to re-check rights at the resource | D |
| C32 | Agent tokens are bound to the MCP server, last minutes, are never forwarded, and are revoked at logout or when a grading run ends | The M1 design never fixed token rules | E |
| C33 | The MCP server returns fixed error codes and never echoes request text back | Error text is an injection channel back into a model | C |
| C34 | `store_proposed_grade` takes the ID of a checked grading result, never a score | The orchestrator could otherwise store any in-range score | C |
| C35 | The course-material search for grading moves into the context assembler (code); the orchestrator never sees excerpts | The planner must never read untrusted text (Week 8 planner–executor rule; closes part of T-03) | C |
| C36 | The review screen shows the instructor the exact text the grader read and flags full marks, outliers and disagreements between the two grading runs | Makes hidden text visible and fights confirmation fatigue (the residual risk on essays) | A, C |
| C37 | The instructor agent gets a `list_appeals` tool; the audit view and manual grading queue get screens | Closes the two gaps found in M1 (no tool fetched appeals; D6 and D11 were never read) | C, A |
| — | Rubrics are stored as structured criteria with maximum marks, never only as a PDF | The output validator (C02) needs the maximums | D, A |
| — | `grade_submission` and `check_citations` are local tools inside the grading agent; the MCP server serves the data tools | Matches the Level 1 diagram (F10, F11 go straight to the grading agent); fixes a wrong sentence in M1 report Section 2.2 | C, B |
| — | Cited URLs are extracted from the submission by code; the grader no longer lists them | No model decides which address the fetcher visits (shrinks T-07 and T-08) | C, D |
| — | The release email contains no model-written text, only a fixed message and a link to the app | Removes the injected-link and header paths (T-11, T-33) by design instead of by filtering | D |
| — | Documents are parsed in a separate container with no network and no credentials | A malicious parser library (T-15) has nothing to steal and nowhere to send it | E, D |
| — | Objective answers are submitted as separate fields per criterion | Code can mark them against the key without a model (C20) | D, A |

## 2. Dates

Today is Sunday 22 November. The brief says code and report are due "Monday 9 December" and presentations are on 10 December. **In 2026, 9 December is a Wednesday.** Person A asks the instructor which date is right; until then, plan for Wednesday 9 December and treat Monday 7 December as a soft deadline.

| Date | Milestone | What must be true |
|---|---|---|
| Tue 24 Nov | Foundations | Repo, Compose stack, database schema, CI skeleton and test framework merged; `make up` starts every service |
| Wed 25 Nov | Identity and adapters | Login (with instructor second factor), agent tokens, model adapter with fake model, MCP server skeleton, React shell |
| **Fri 27 Nov** | **Walking skeleton** | With the fake model: instructor creates an assignment with a rubric, student submits, grading run proposes a grade, instructor approves, release service publishes, student sees the grade, email appears in Mailpit, audit log shows every tool call |
| Thu 3 Dec | Features complete | Chat, instructor agent, appeals, blog, web checking, retrieval, exports, pause switch, alerts; real provider plugged in if keys have arrived |
| **Fri 4 Dec** | **Feature freeze** | Every Critical and High threat (T-01 to T-29) has a verification test in `tests/verification/`; CI is green with all gates on |
| Sat 5 – Mon 7 Dec | Evidence and report | Probabilistic tests run repeatedly on the real model; remediation log closed; matrix complete; each owner's report sections drafted |
| Tue 8 Dec | Final assembly | Report assembled (30 pages maximum excluding appendices); a teammate who didn't write the setup runs the README on a clean machine; demo rehearsed twice |
| Wed 9 Dec | Submit | Repository, report, matrix, SBOM and remediation log, system card, slides |
| Thu 10 Dec | Present | 10-minute demo and talk, 5 minutes of Q&A; every member presents |
| Week 13 (date set by instructors) | Advisory drill | 72-hour exposure note, answered from the SBOM; E leads, everyone on call |

## 3. Who owns what

Roles say who leads an area, not who does all of it. Every member writes code, writes verification tests, and must be able to answer questions on any part of the system.

| Area | Lead | Main files |
|---|---|---|
| React front end, main workflow, review and approval screens, BO metrics, system card, residual risk, demo narrative | A | `frontend/`, `docs/system-card.md` |
| Verification framework, authorization tests, threat-model revision, revised DFDs, traceability matrix, report editing | B | `tests/verification/`, `tests/authz/`, `docs/threat-model/` |
| Model adapter, MCP server, grading agent, chat agent, instructor agent, prompts | C | `backend/agents/`, `backend/mcp_server/`, `backend/llm/`, `prompts/` |
| Database schema and row-level security, seed data, ingestion, retrieval, fetcher, output sinks, release service | D | `backend/db/`, `backend/ingestion/`, `backend/retrieval/`, `backend/fetcher/`, `backend/release/`, `seed/` |
| Repo and Compose, identities and credentials, CI gates, SBOM, supply chain, monitoring, kill switch, runbook | E | `deploy/`, `.github/`, `backend/identity/`, `scripts/`, `docs/runbook.md`, `aibom/` |

### Milestone 2 deliverables and owners

| Deliverable (brief 5.3) | Owner | Contributors |
|---|---|---|
| Repository with README that runs locally, seed generation, one-command test suite, lockfiles, SBOM step, scanning gates | E | all |
| Final Security Report, 30 pages maximum | B (editor) | all |
| §1 Threat-model revision | B | all |
| §2 Control implementation | B | each control owner writes their rows |
| §3 Verification evidence | B | each test owner |
| §4 Supply-chain remediation (SBOM, scans, remediation log, advisory-drill note) | E | D (models, datasets) |
| §5 Development pipeline security and AI-assisted development policy | E | all (tool disclosure) |
| §6 Runtime monitoring and incident response | E | C |
| §7 Governance: system card, audit-trail design, disclosure statement | A | C, E |
| §8 Residual risk | A | B |
| §9 Lessons learned and contribution log | A | all |
| Completed traceability matrix | B | all |
| SBOM and remediation log | E | D |
| Slides and demo | A | all present |

### Requirements R1–R11 and where they are met

| Req | How it's met | Owner |
|---|---|---|
| R1 agent loop | Grading orchestrator, chat agent and instructor agent each run a tool-use loop | C |
| R2 three tools, one with a side effect | `store_proposed_grade`, `open_appeal`, `draft_assignment`, `propose_grade_change` all write | C |
| R3 MCP server | Team-built gradebook and search MCP server | C |
| R4 RAG with untrusted ingestion | Instructor uploads (including third-party chapters), blog comments, cited web pages | D |
| R5 output sink beyond chat | Rendered Markdown feedback, release email, CSV export, database writes | D, A |
| R6 two roles and a distinct agent identity | Student and instructor roles; each agent has its own service identity and token | E |
| R7 model-sourcing decision | Written when the provider is known: provider data handling, retention, our exposure | C |
| R8 isolation pattern | Dual-LLM split: quarantined grader and evidence checker without tools; orchestrator never reads untrusted text | C |
| R9 CI gates and tool-call audit log | GitHub Actions gates; append-only, hash-chained audit log written by the MCP server | E, C |
| R10 human approval | Release of grades, publishing assignments, accepting answer keys, deciding appeals | A, D |
| R11 SBOM and AI-BOM in CI | CycloneDX for Python, npm and images, merged with a maintained AI-BOM for models and datasets | E |

## 4. How we work

- **Branches and reviews.** `main` is protected. Every change goes through a pull request reviewed by one other member. Changes to `01-interfaces.md`, `deploy/`, `.github/`, `backend/identity/`, `backend/mcp_server/tools.py` and `CLAUDE.md` need the owner listed in `CODEOWNERS`.
- **AI coding assistants.** Allowed, and part of our attack surface. Every PR says in its template whether an assistant wrote part of it and which one. The reviewer reads AI-written code line by line. Assistants follow `CLAUDE.md` (E writes it): no secrets, no real personal data, run the admission check before adding any dependency, never edit lockfiles by hand. Each member lists the assistants and editor extensions they use in the inventory (row SC-51).
- **New dependencies.** Before any new package is merged, run `scripts/admission_check.py <pypi|npm> <package>`, which checks that it exists, that it's the package you meant, and that its maintainer history is credible. Paste the output in the PR. E adds the row to the inventory.
- **Commits.** Small, frequent, in your own name. The commit history is the brief's evidence of individual contribution.
- **Canaries, not payloads.** Every injection test uses a harmless canary such as `CANARY-T04-7f3a` or an instruction to call a logging tool. Never write real attack payloads.
- **Synthetic data only.** All users, courses and submissions come from the seed generator. Email goes only to Mailpit.
- **Budget.** Set spending caps on the provider account the moment keys arrive (E). Probabilistic tests against the real model are run deliberately, not on every push.
- **Daily check-in.** Five lines in the team chat each evening: done, next, blocked, any interface change, any new threat you noticed. New threats go to B the same day.

## 5. The demo we are building towards

Person A owns the script; B owns the control demos. The brief asks for the main workflow end to end, then at least three controls acting on canary inputs, including the R8 isolation pattern and one human-approval gate, the audit-log entries they produced, one remediated supply-chain finding with before-and-after scans, and residual risk.

1. Instructor uploads slides and a third-party chapter, approves them, and publishes an assignment with a structured rubric.
2. Student asks the chat agent about the slides, submits an answer citing a web page, and later asks why marks were lost.
3. Instructor starts grading. Proposed grades appear in the review queue with flags; the instructor approves after re-authenticating; the student sees the grade; the email is in Mailpit.
4. **Control 1 (R8 isolation, T-04):** a submission carrying `CANARY-T04` hidden text. The grader's score stays within the rubric, the orchestrator's logged context never contains the submission text, and the review screen shows the hidden sentence.
5. **Control 2 (human approval, T-02):** an appeal carrying a canary asking for a grade change. The instructor agent can only propose; nothing changes until the instructor confirms on a screen that shows the real data.
6. **Control 3 (identity, T-05):** a chat message claiming another student's ID. The MCP server ignores it, serves only the signed-in student's feedback, and logs the denial.
7. Audit-log view showing the entries from steps 4 to 6.
8. Supply chain: one real finding from our scans, its fix, and the clean re-scan.
9. Residual risk: a believable but wrong in-range score on an essay, and how we measure it.
