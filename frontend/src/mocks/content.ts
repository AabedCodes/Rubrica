/**
 * MOCK(D6): assignment, rubric, answer-key and submission routes.
 * Mirrors the rules in docs/plan/D-data-retrieval-engineer.md D6 and §3.1:
 * course membership and role checks (C29), max_points > 0, keys stored as
 * draft, one current submission per student, only before the due date.
 */
import type { AnswerKeyEntry, Assignment, AssignmentSummary, CriterionInput, MySubmission } from "../types/content";
import { error, isRecord, json, route, type MockContext, type MockHandler, type MockRequest } from "./http";
import { visibleAssignment } from "./access";
import { releasedGradeFor } from "./grading";
import type { MockAssignment } from "./state";

export function toAssignment(a: MockAssignment): Assignment {
  return {
    id: a.id,
    course_id: a.course_id,
    title: a.title,
    instructions: a.instructions,
    status: a.status,
    due_at: a.due_at,
    version: a.version,
    criteria: a.criteria.map((c) => ({ ...c })),
  };
}

function toSummary(a: MockAssignment): AssignmentSummary {
  return { id: a.id, course_id: a.course_id, title: a.title, status: a.status, due_at: a.due_at };
}

function validCriteria(value: unknown): CriterionInput[] | null {
  if (!Array.isArray(value) || value.length === 0) return null;
  const out: CriterionInput[] = [];
  for (const row of value) {
    if (!isRecord(row)) return null;
    const { label, max_points, kind } = row;
    if (typeof label !== "string" || !label.trim() || label.length > 500) return null;
    if (typeof max_points !== "number" || !(max_points > 0) || max_points > 100 || (max_points * 2) % 1 !== 0) return null;
    if (kind !== "objective" && kind !== "open") return null;
    out.push({ label: label.trim(), max_points, kind });
  }
  return out;
}

function validKeyEntries(value: unknown, a: MockAssignment): AnswerKeyEntry[] | null {
  if (!Array.isArray(value)) return null;
  const out: AnswerKeyEntry[] = [];
  for (const row of value) {
    if (!isRecord(row)) return null;
    const criterion = a.criteria.find((c) => c.id === row.criterion_id);
    if (!criterion || typeof row.content !== "string") return null;
    let expected: AnswerKeyEntry["expected"] = null;
    if (criterion.kind === "objective") {
      const e = row.expected;
      if (!isRecord(e)) return null;
      if (e.type === "choice" && typeof e.value === "string" && e.value.trim()) expected = { type: "choice", value: e.value.trim() };
      else if (e.type === "numeric" && typeof e.value === "number" && typeof e.tolerance === "number" && e.tolerance >= 0)
        expected = { type: "numeric", value: e.value, tolerance: e.tolerance };
      else return null;
    }
    out.push({ criterion_id: criterion.id, content: row.content, expected });
  }
  return out;
}

function instructorOnly(ctx: MockContext): Response | null {
  return ctx.user.role === "instructor" ? null : error(403, "forbidden");
}

export const contentHandler: MockHandler = (req: MockRequest, ctx: MockContext) => {
  let p: Record<string, string> | null;

  // MOCK(D6): ASSUMED route GET /courses/{id}/assignments
  if ((p = route("GET", "/api/courses/:courseId/assignments", req))) {
    if (!ctx.enrolledIn(p.courseId!)) return error(404, "not_found");
    const list = ctx.world.assignments.filter(
      (a) => a.course_id === p!.courseId && (ctx.user.role === "instructor" || a.status === "published"),
    );
    return json(200, list.map(toSummary));
  }

  // MOCK(D6): §10 POST /courses/{id}/assignments
  if ((p = route("POST", "/api/courses/:courseId/assignments", req))) {
    if (!ctx.enrolledIn(p.courseId!)) return error(404, "not_found");
    const denied = instructorOnly(ctx);
    if (denied) return denied;
    const b = req.body;
    if (!isRecord(b) || typeof b.title !== "string" || !b.title.trim() || typeof b.instructions !== "string" || typeof b.due_at !== "string" || Number.isNaN(Date.parse(b.due_at)))
      return error(400, "invalid_request");
    const a: MockAssignment = {
      id: ctx.world.newId(),
      course_id: p.courseId!,
      title: b.title.trim(),
      instructions: b.instructions,
      status: "draft",
      due_at: new Date(b.due_at).toISOString(),
      version: 1,
      criteria: [],
      answerKey: null,
    };
    ctx.world.assignments.push(a);
    return json(201, toAssignment(a));
  }

  // MOCK(D6): ASSUMED route GET /assignments/{id}
  if ((p = route("GET", "/api/assignments/:id", req))) {
    const a = visibleAssignment(ctx, p.id);
    return a ? json(200, toAssignment(a)) : error(404, "not_found");
  }

  // MOCK(D6): §10 PUT /assignments/{id}/rubric
  if ((p = route("PUT", "/api/assignments/:id/rubric", req))) {
    const a = visibleAssignment(ctx, p.id);
    if (!a) return error(404, "not_found");
    const denied = instructorOnly(ctx);
    if (denied) return denied;
    if (a.status !== "draft") return error(400, "invalid_request"); // ASSUMED: rubric locked once published
    const criteria = validCriteria(isRecord(req.body) ? req.body.criteria : undefined);
    if (!criteria) return error(400, "invalid_request");
    a.criteria = criteria.map((c, position) => ({ ...c, id: ctx.world.newId(), position }));
    a.answerKey = null; // criterion IDs changed, so any old key no longer applies
    a.version += 1;
    return json(200, toAssignment(a));
  }

  // MOCK(D6): ASSUMED route GET /assignments/{id}/answer-key (instructors only, T-01)
  if ((p = route("GET", "/api/assignments/:id/answer-key", req))) {
    const a = visibleAssignment(ctx, p.id);
    if (!a) return error(404, "not_found");
    const denied = instructorOnly(ctx);
    if (denied) return denied;
    return a.answerKey ? json(200, a.answerKey) : error(404, "not_found");
  }

  // MOCK(D6): §10 PUT /assignments/{id}/answer-key (stored as draft)
  if ((p = route("PUT", "/api/assignments/:id/answer-key", req))) {
    const a = visibleAssignment(ctx, p.id);
    if (!a) return error(404, "not_found");
    const denied = instructorOnly(ctx);
    if (denied) return denied;
    const entries = validKeyEntries(isRecord(req.body) ? req.body.entries : undefined, a);
    if (!entries) return error(400, "invalid_request");
    a.answerKey = { assignment_id: a.id, status: "draft", version: (a.answerKey?.version ?? 0) + 1, entries };
    return json(200, a.answerKey);
  }

  // MOCK(D6): §10 POST /assignments/{id}/publish (re-auth, C28)
  if ((p = route("POST", "/api/assignments/:id/publish", req))) {
    const a = visibleAssignment(ctx, p.id);
    if (!a) return error(404, "not_found");
    const denied = instructorOnly(ctx);
    if (denied) return denied;
    if (!ctx.reauthFresh()) return error(401, "reauth_required");
    if (a.criteria.length === 0) return error(400, "invalid_request");
    a.status = "published";
    return json(200, toAssignment(a));
  }

  // MOCK(D6): §10 POST /assignments/{id}/submissions (multipart, students only)
  if ((p = route("POST", "/api/assignments/:id/submissions", req))) {
    const a = visibleAssignment(ctx, p.id);
    if (!a) return error(404, "not_found");
    if (ctx.user.role !== "student") return error(403, "forbidden");
    if (ctx.now() > Date.parse(a.due_at)) return error(400, "deadline_passed");
    const form = req.body;
    if (!(form instanceof FormData)) return error(400, "invalid_request");
    const text = form.get("body_text");
    const rawAnswers = form.get("objective_answers");
    const file = form.get("file");
    let answers: unknown;
    try {
      answers = typeof rawAnswers === "string" ? JSON.parse(rawAnswers) : {};
    } catch {
      return error(400, "invalid_request");
    }
    if (typeof text !== "string" || !isRecord(answers)) return error(400, "invalid_request");
    if (file !== null && (!(file instanceof File) || file.type !== "application/pdf")) return error(400, "invalid_request");
    const objective: Record<string, string> = {};
    for (const c of a.criteria.filter((x) => x.kind === "objective")) {
      const v = answers[c.id];
      if (typeof v === "string") objective[c.id] = v;
    }
    // One current submission per student: replace any earlier one (D6).
    ctx.world.submissions = ctx.world.submissions.filter((s) => !(s.assignment_id === a.id && s.student_id === ctx.user.id));
    const id = ctx.world.newId();
    ctx.world.submissions.push({
      id,
      assignment_id: a.id,
      student_id: ctx.user.id,
      body_text: text,
      objective_answers: objective,
      file_name: file instanceof File ? file.name : null,
      submitted_at: new Date(ctx.now()).toISOString(),
    });
    return json(201, { id });
  }

  // MOCK(D6): §10 GET /assignments/{id}/my-submission
  if ((p = route("GET", "/api/assignments/:id/my-submission", req))) {
    const a = visibleAssignment(ctx, p.id);
    if (!a) return error(404, "not_found");
    const s = ctx.world.submissions.find((x) => x.assignment_id === a.id && x.student_id === ctx.user.id);
    if (!s) return error(404, "not_found");
    const body: MySubmission = {
      id: s.id,
      submitted_at: s.submitted_at,
      body_text: s.body_text,
      objective_answers: { ...s.objective_answers },
      file_name: s.file_name,
      grade: releasedGradeFor(ctx.world, a, s.id),
    };
    return json(200, body);
  }

  return undefined;
};
