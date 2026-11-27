# A6: Chat panel, appeals, blog, materials

- **Author:** A (@JoudyElGayar)
- **Date finished:** 2026-11-28
- **PR / commits:** PR not opened yet. Commit on branch `A/A6-chat-appeals-blog-materials`, stacked on `A/A7-confirm-audit-pause` (which sits on #17). A6 reuses A7's appeals, audit and pause mocks and A5's extracted-text view.
- **Threats / controls:** C01 (trust labels), C04 (publish after reading the extracted text), C07 (SafeMarkdown for all model and blog text), C23 (fixed answer-key notice), C24 (blog untrusted), C30; T-03, T-05, T-09, and T-06/T-13/T-20 (blog canaries shown as plain, labelled text)
- **Feeds report sections:** §2, §3
- **AI assistance:** Claude Code (desktop app, Claude Opus 5.5) wrote the screens, the mocked routes, the tests and this entry, under A's direction. A asked for chat replies to go only through SafeMarkdown and for every mocked route to be tagged.

## What was done

- **Chat panel** (`/courses/:id/chat`, students):
  - Replies are shown only through `SafeMarkdown`, labelled "Answered by the AI assistant", with a badge for each source: "Instructor material", "Third-party source", "Instructor blog post", "Comment by a student".
  - C23's fixed answer-key notice and a pause notice appear as system notes, never as model text.
  - Questions can be prefilled from `?q=`.
- **Grade actions,** under every released grade (My grades and the assignment page):
  - "Ask about this grade" opens the chat with the question filled in.
  - "Appeal" opens a form with a 2,000-character limit and counter, the same limit as `open_appeal` (§5). Sending tells the student their grade changes only if the instructor accepts a change.
- **Blog** (`/courses/:id/blog`, all members):
  - posts and comments rendered through `SafeMarkdown`;
  - each item labelled "Instructor blog post", "Comment by a student" or "Comment by the instructor";
  - instructors can post and delete; members can comment.
- **Materials** (`/courses/:id/materials`, instructors):
  - upload a PDF with a "Third-party source" option, refusing other files;
  - parse status and publication status;
  - a detail page showing the extracted text with invisible characters marked (A5's view);
  - an effect line saying what publishing does;
  - Publish behind re-auth (C04).
- **Mocks:**
  - `MOCK(C6)`: a scripted chat agent and the student appeal route.
  - `MOCK(D7)`: blog.
  - `MOCK(D6)`: materials.
  - **Seed data:** one instructor post; student comments carrying D2's `CANARY-T06-2b11`, `CANARY-T13-426e` and `CANARY-T20-0f9c`; published lecture notes; and a **pending third-party chapter** whose hidden line is a zero-width space followed by D2's `CANARY-T03-065e`.

## How

- **Code:** shapes in `src/types/student.ts`, wrappers in `studentRoutes`, screens in `src/pages/student/`, and `GradeActions` in `src/components/`.
- **Scripted chat agent:** it matches on the message the way FakeLLM is scripted (§6):
  - key questions get the C23 notice;
  - questions about another student get "your own feedback only" plus a denied `get_my_feedback` audit row (T-05);
  - "diagram" adds D2's T-09 fixture image, which `SafeMarkdown` turns into text.
- **Appeals and pause:** an appeal from the form appears in A7's appeals list. A paused course (A7) returns the pause notice.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Appeals through a plain form (`POST /submissions/{id}/appeals`) | Only through the chat agent's `open_appeal` | The plan says "agree with C which". A form is deterministic and doesn't depend on a model; it writes the same row. Raised with C as an open question |
| One open appeal per submission, only after release | Any number | Release is the human-approval line (R10); several open appeals for one grade would spread the decision |
| Student-written text (appeals, comments) shown as plain text or `SafeMarkdown`, never as HTML | Rich text | C07: blog text is untrusted (TB-5) |
| Chat is students only (instructor chat → 403) | Both roles | The chat agent holds a `student_delegate` token (§4.2, §5); the instructor agent (C7) is a separate tool |
| Materials list and extracted text as new routes | Reuse the submissions route | §10 has upload and publish only; C04 needs the text read before publishing |
| Upload refuses non-PDF files in the browser | Rely on the server | Faster feedback; the server must check too (mock does) |

## Deviations from the plan or `01-interfaces.md`

`01-interfaces.md` was **not** changed. Items for the next §10 proposal:

1. **Body of `POST /courses/{id}/chat`:** `{conversation_id, reply: {text, sources: [{label, trust}]} | null, notice}`.
2. **`POST /submissions/{id}/appeals` `{reason_text}`:** a decision is needed from C on the form path versus chat-only.
3. **Blog:** delete paths (`DELETE /posts/{id}`, `DELETE /comments/{id}`) and posts returned with their comments.
4. **`GET /courses/{id}/materials`** and **`GET /materials/{id}/extracted-text`**; upload as multipart `{title, source_kind, file}`.

## Evidence

- **Vitest: 103 passed in 13 files,** 10 new in `src/pages/student/student.test.tsx`:
  - **Chat:**
    - no `<img>`, and the T-09 fixture becomes "[image removed: fixture]";
    - source badges "Instructor material: Synthetic lecture notes" and "Comment by a student: …";
    - the C23 notice replaces the reply;
    - an "another student" question gets "your own" feedback only;
    - a paused course returns the pause notice.
  - **Ask about this grade:** opens the chat with the exact question prefilled.
  - **Appeal:** an instructor releases Student Three's grade from the manual queue, Student Three appeals (counter "54 / 2000"), and the instructor sees it as "Open: no proposal yet".
  - **Blog:**
    - Markdown bold renders as `<strong>`;
    - the T-06 canary comment is labelled "Comment by a student";
    - a student comment appears labelled;
    - students see no delete buttons; the instructor deletes the comment.
  - **Materials:**
    - the chapter row shows "Third-party source / Not published";
    - its text shows the `⟦U+200B⟧` marker before `CANARY-T03-065e`;
    - the effect line mentions the third-party label;
    - Publish goes through the re-auth modal;
    - a `.txt` upload is refused; a PDF upload appears as a pending third-party source.
  - **Mock rules:** students get 403 on materials and posting; 404 on someone else's submission; instructors get 403 on chat.
- **Gates.** `make lint` passes. `make test`: Vitest 103 passed; pytest 36 passed, 14 skipped by design.
- **Production build:** no mock traces (`CANARY-T…`, `example.test`, the T-09 fixture URL). No hidden characters in the source.

## Open items

- **Merge order:** after #17 and A7, retarget to `main`.
- **The §10 items above** (C, D).
- **Decision from C:** appeals by form, chat or both.
- **Switching to the real API:** `MOCK(C6)`, `MOCK(D7)` and `MOCK(D6)` as C6, D6 and D7's routes land. The blog and ingestion back end (D7) is already merged without routes.
