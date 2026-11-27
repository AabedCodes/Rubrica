/**
 * A6 mocked routes: chat (MOCK(C6)), the student appeal form (MOCK(C6)),
 * course blog (MOCK(D7)) and materials (MOCK(D6)).
 *
 * The chat agent is scripted like FakeLLM (01-interfaces.md §6): fixed replies
 * chosen by simple matches on the message, never a model.
 */
import type { Author, BlogComment, BlogPost, ChatResponse, Material } from "../types/student";
import { MAX_APPEAL_CHARS } from "../types/student";
import { writeAudit } from "./audit";
import { error, isRecord, json, noContent, route, type MockContext, type MockHandler } from "./http";
import { controlsFor } from "./oversight";
import { MOCK_USERS, type MockMaterial, type MockWorld } from "./state";

/** D2's T-09 fixture: a scripted model reply carrying a Markdown image (seed/canaries/T09.json). */
export const T09_REPLY_IMAGE = "![fixture](https://example.edu/rubrica-canaries/CANARY-T09-0c97)";

function author(id: string): Author {
  const u = MOCK_USERS.find((x) => x.id === id);
  return { id, display_name: u?.display_name ?? "Unknown", role: u?.role ?? "student" };
}

function postView(w: MockWorld, p: MockWorld["blogPosts"][number]): BlogPost {
  return {
    id: p.id,
    author: author(p.author_id),
    body: p.body,
    created_at: p.created_at,
    comments: w.blogComments
      .filter((c) => c.post_id === p.id)
      .map((c): BlogComment => ({ id: c.id, author: author(c.author_id), body: c.body, created_at: c.created_at })),
  };
}

function materialView(m: MockMaterial): Material {
  return { id: m.id, title: m.title, source_kind: m.source_kind, status: m.status, parse_status: m.parse_status, uploaded_at: m.uploaded_at };
}

function cleanBody(raw: unknown, max: number): string | null {
  if (!isRecord(raw) || typeof raw.body !== "string") return null;
  const body = raw.body.trim();
  return body && body.length <= max ? body : null;
}

/** Scripted chat agent (MOCK(C6)). */
function chatReply(ctx: MockContext, message: string): Omit<ChatResponse, "conversation_id"> {
  const m = message.toLowerCase();
  // C23: a reply that would reveal answer-key text is replaced by a fixed notice.
  if (/answer key|correct answer|what is the answer/.test(m)) return { reply: null, notice: "answer_key_blocked" };
  // T-05: the token is the signed-in student's; other students' feedback is out of reach.
  if (/another student|student (one|two|three|four)'s|someone else/.test(m)) {
    writeAudit(ctx, { actor_kind: "agent", actor_id: "chat-agent", on_behalf_of: ctx.user.id, action: "get_my_feedback", decision: "denied", reason_code: "E_NOT_FOUND" });
    return { reply: { text: "I can only see **your own** feedback. Ask your instructor about anyone else's work.", sources: [] }, notice: null };
  }
  if (/why did i get|my grade|lost marks/.test(m)) {
    return {
      reply: {
        text: "Your feedback says the answer *names* the idea but doesn't explain **why** it matters for grading. The lecture notes cover this in Lecture 1.",
        sources: [{ label: "Synthetic lecture notes", trust: "instructor" }],
      },
      notice: null,
    };
  }
  return {
    reply: {
      text: `A trust boundary is where data or control passes between parties that trust each other differently.\n\n${/diagram|picture/.test(m) ? T09_REPLY_IMAGE : ""}\n\nA student on the blog also mentioned labels on retrieved text.`,
      sources: [
        { label: "Synthetic lecture notes", trust: "instructor" },
        { label: "Course blog comment", trust: "student_comment" },
      ],
    },
    notice: null,
  };
}

export const studentHandler: MockHandler = (req, ctx) => {
  const w = ctx.world;
  let p: Record<string, string> | null;

  // MOCK(C6): §10 POST /courses/{id}/chat (students; C22 tools; C23 key check)
  if ((p = route("POST", "/api/courses/:id/chat", req))) {
    if (!ctx.enrolledIn(p.id!)) return error(404, "not_found");
    if (ctx.user.role !== "student") return error(403, "forbidden");
    const b = isRecord(req.body) ? req.body : {};
    const message = typeof b.message === "string" ? b.message.trim() : "";
    if (!message || message.length > 2000) return error(400, "invalid_request");
    const conversation_id = typeof b.conversation_id === "string" ? b.conversation_id : w.newId();
    if (controlsFor(w, p.id!).agents_paused) return json(200, { conversation_id, reply: null, notice: "agents_paused" });
    return json(200, { conversation_id, ...chatReply(ctx, message) });
  }

  // MOCK(C6): ASSUMED route POST /submissions/{id}/appeals (the plain-form path; same rules as open_appeal)
  if ((p = route("POST", "/api/submissions/:id/appeals", req))) {
    const s = w.submissions.find((x) => x.id === p!.id);
    // Only the student's own submission, and only once its grade is released (R10).
    if (!s || ctx.user.role !== "student" || s.student_id !== ctx.user.id) return error(404, "not_found");
    if (!w.proposed.some((g) => g.submission_id === s.id && g.status === "released")) return error(400, "invalid_request");
    const reason = isRecord(req.body) && typeof req.body.reason_text === "string" ? req.body.reason_text.trim() : "";
    if (!reason || reason.length > MAX_APPEAL_CHARS) return error(400, "invalid_request");
    if (w.appeals.some((a) => a.submission_id === s.id && a.status !== "decided")) return error(400, "invalid_request");
    const id = w.newId();
    w.appeals.push({ id, submission_id: s.id, student_id: ctx.user.id, reason_text: reason, status: "open", created_at: new Date(ctx.now()).toISOString() });
    const courseId = w.assignments.find((a) => a.id === s.assignment_id)?.course_id ?? null;
    writeAudit(ctx, { action: "open_appeal", course_id: courseId, args_redacted: { submission_id: s.id, reason_text: { length: reason.length, sha256: "mock" } }, result_summary: { appeal_id: id } });
    return json(201, { appeal_id: id });
  }

  // MOCK(D7): §10 GET and POST /courses/{id}/blog/posts (posts: instructors)
  if ((p = route("GET", "/api/courses/:id/blog/posts", req))) {
    if (!ctx.enrolledIn(p.id!)) return error(404, "not_found");
    return json(200, w.blogPosts.filter((x) => x.course_id === p!.id).map((x) => postView(w, x)));
  }
  if ((p = route("POST", "/api/courses/:id/blog/posts", req))) {
    if (!ctx.enrolledIn(p.id!)) return error(404, "not_found");
    if (ctx.user.role !== "instructor") return error(403, "forbidden");
    const body = cleanBody(req.body, 10_000);
    if (!body) return error(400, "invalid_request");
    const post = { id: w.newId(), course_id: p.id!, author_id: ctx.user.id, body, created_at: new Date(ctx.now()).toISOString() };
    w.blogPosts.push(post);
    return json(201, postView(w, post));
  }

  // MOCK(D7): §10 POST /posts/{id}/comments (course members)
  if ((p = route("POST", "/api/posts/:id/comments", req))) {
    const post = w.blogPosts.find((x) => x.id === p!.id);
    if (!post || !ctx.enrolledIn(post.course_id)) return error(404, "not_found");
    const body = cleanBody(req.body, 2000);
    if (!body) return error(400, "invalid_request");
    const c = { id: w.newId(), post_id: post.id, author_id: ctx.user.id, body, created_at: new Date(ctx.now()).toISOString() };
    w.blogComments.push(c);
    return json(201, { id: c.id, author: author(c.author_id), body: c.body, created_at: c.created_at });
  }

  // MOCK(D7): §10 DELETE for instructors (ASSUMED paths /posts/{id} and /comments/{id}); also removes the indexed chunks (D7)
  if ((p = route("DELETE", "/api/posts/:id", req)) || (p = route("DELETE", "/api/comments/:id", req))) {
    const isPost = req.path.startsWith("/api/posts/");
    const courseId = isPost
      ? w.blogPosts.find((x) => x.id === p!.id)?.course_id
      : w.blogPosts.find((x) => x.id === w.blogComments.find((c) => c.id === p!.id)?.post_id)?.course_id;
    if (!courseId || !ctx.enrolledIn(courseId)) return error(404, "not_found");
    if (ctx.user.role !== "instructor") return error(403, "forbidden");
    if (isPost) {
      w.blogPosts = w.blogPosts.filter((x) => x.id !== p!.id);
      w.blogComments = w.blogComments.filter((c) => c.post_id !== p!.id);
    } else {
      w.blogComments = w.blogComments.filter((c) => c.id !== p!.id);
    }
    writeAudit(ctx, { action: isPost ? "delete_blog_post" : "delete_blog_comment", course_id: courseId, args_redacted: { id: p.id } });
    return noContent();
  }

  // MOCK(D6): ASSUMED route GET /courses/{id}/materials (instructors)
  if ((p = route("GET", "/api/courses/:id/materials", req))) {
    if (!ctx.enrolledIn(p.id!)) return error(404, "not_found");
    if (ctx.user.role !== "instructor") return error(403, "forbidden");
    return json(200, w.materials.filter((m) => m.course_id === p!.id).map(materialView));
  }

  // MOCK(D6): §10 POST /courses/{id}/materials (multipart: title, source_kind, file)
  if ((p = route("POST", "/api/courses/:id/materials", req))) {
    if (!ctx.enrolledIn(p.id!)) return error(404, "not_found");
    if (ctx.user.role !== "instructor") return error(403, "forbidden");
    const form = req.body;
    if (!(form instanceof FormData)) return error(400, "invalid_request");
    const title = form.get("title");
    const kind = form.get("source_kind");
    const file = form.get("file");
    if (typeof title !== "string" || !title.trim() || (kind !== "instructor" && kind !== "third_party")) return error(400, "invalid_request");
    if (!(file instanceof File) || file.type !== "application/pdf") return error(400, "invalid_request");
    // The isolated parser (D4) would extract the text; the mock records a placeholder.
    const m: MockMaterial = {
      id: w.newId(),
      course_id: p.id!,
      title: title.trim(),
      source_kind: kind,
      status: "pending",
      parse_status: "parsed",
      uploaded_at: new Date(ctx.now()).toISOString(),
      text: `Extracted text of ${file.name} (mock parser output).`,
    };
    w.materials.push(m);
    writeAudit(ctx, { action: "upload_material", course_id: p.id!, args_redacted: { material_id: m.id, source_kind: kind } });
    return json(201, materialView(m));
  }

  // MOCK(D6): ASSUMED route GET /materials/{id}/extracted-text (instructors, C04)
  if ((p = route("GET", "/api/materials/:id/extracted-text", req))) {
    const m = w.materials.find((x) => x.id === p!.id);
    if (!m || ctx.user.role !== "instructor" || !ctx.enrolledIn(m.course_id)) return error(404, "not_found");
    return json(200, { material_id: m.id, text: m.text });
  }

  // MOCK(D6): §10 POST /materials/{id}/publish (re-auth, C04, C28)
  if ((p = route("POST", "/api/materials/:id/publish", req))) {
    const m = w.materials.find((x) => x.id === p!.id);
    if (!m || ctx.user.role !== "instructor" || !ctx.enrolledIn(m.course_id)) return error(404, "not_found");
    if (!ctx.reauthFresh()) return error(401, "reauth_required");
    if (m.status !== "pending" || m.parse_status !== "parsed") return error(400, "invalid_request");
    m.status = "published";
    writeAudit(ctx, { action: "publish_material", course_id: m.course_id, args_redacted: { material_id: m.id, source_kind: m.source_kind } });
    return json(200, materialView(m));
  }

  return undefined;
};
