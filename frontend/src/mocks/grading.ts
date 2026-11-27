/**
 * MOCK(C4) grading runs and MOCK(D3) approve-and-release, scripted like the
 * fake model (01-interfaces.md §6): no model is involved.
 *
 * Follows §7 where it matters for the screens:
 * - objective criteria are marked by code against the key (C20);
 * - two attempts per open criterion; proposed score = mean rounded down to 0.5;
 * - flags: full_marks, disagreement (attempts differ by more than one point);
 * - totals are computed by code from the scores.
 * The submission with the CANARY-T04 line plays a fooled grader (full marks).
 */
import type { ReleasedGrade } from "../types/content";
import type { ApproveResponse, GradeFlag, ProposedGradeRow, StartRunResponse } from "../types/grading";
import { visibleAssignment } from "./access";
import { error, isRecord, json, route, type MockContext, type MockHandler } from "./http";
import { MOCK_USERS, type MockAssignment, type MockProposedGrade, type MockSubmission, type MockWorld } from "./state";

const floorHalf = (n: number) => Math.floor(n * 2) / 2;
const clamp = (n: number, max: number) => Math.min(Math.max(n, 0), max);

function markObjective(a: MockAssignment, s: MockSubmission, criterionId: string): number {
  const criterion = a.criteria.find((c) => c.id === criterionId)!;
  const expected = a.answerKey?.entries.find((e) => e.criterion_id === criterionId)?.expected;
  const answer = (s.objective_answers[criterionId] ?? "").trim();
  if (!expected || !answer) return 0;
  if (expected.type === "choice") return answer.toUpperCase() === expected.value.toUpperCase() ? criterion.max_points : 0;
  const n = Number(answer);
  return Number.isFinite(n) && Math.abs(n - expected.value) <= expected.tolerance ? criterion.max_points : 0;
}

function gradeSubmission(world: MockWorld, a: MockAssignment, s: MockSubmission, index: number): MockProposedGrade {
  const fooled = s.body_text.includes("CANARY-T04"); // scripted "fooled grader" for the demo
  const words = s.body_text.split(/\s+/).filter(Boolean).length;
  const attempt1: Record<string, number> = {};
  const attempt2: Record<string, number> = {};
  const proposed: Record<string, number> = {};
  const feedback: Record<string, string> = {};
  const flags = new Set<GradeFlag>();

  a.criteria.forEach((c, i) => {
    if (c.kind === "objective") {
      const mark = markObjective(a, s, c.id);
      attempt1[c.id] = attempt2[c.id] = proposed[c.id] = mark;
      return;
    }
    const base = fooled ? c.max_points : clamp(floorHalf(words / 12 + i), c.max_points);
    const second = index === 1 && i === 1 ? clamp(base - 1.5, c.max_points) : base; // one scripted disagreement
    attempt1[c.id] = base;
    attempt2[c.id] = second;
    proposed[c.id] = floorHalf((base + second) / 2);
    if (Math.abs(base - second) > 1) flags.add("disagreement");
    feedback[c.id] = fooled
      ? "Excellent work on every point. ![badge](https://canary.example/?d=CANARY-T09-4e2f)"
      : "**Partly meets the criterion.** The answer names the idea; explain *why* it matters for grading.";
  });

  const total = a.criteria.reduce((sum, c) => sum + (proposed[c.id] ?? 0), 0);
  const max_total = a.criteria.reduce((sum, c) => sum + c.max_points, 0);
  if (total === max_total && max_total > 0) flags.add("full_marks");

  return {
    id: world.newId(),
    assignment_id: a.id,
    submission_id: s.id,
    attempts: [attempt1, attempt2],
    proposed,
    feedback,
    flags: [...flags],
    total,
    max_total,
    status: "pending",
    released_at: null,
  };
}

/** The released grade a student may see, or null before release (R10). */
export function releasedGradeFor(world: MockWorld, a: MockAssignment, submissionId: string): ReleasedGrade | null {
  const g = world.proposed.find((x) => x.submission_id === submissionId && x.status === "released");
  if (!g || !g.released_at) return null;
  return {
    total: g.total,
    max_total: g.max_total,
    released_at: g.released_at,
    criteria: a.criteria.map((c) => ({
      criterion_id: c.id,
      label: c.label,
      kind: c.kind,
      max_points: c.max_points,
      score: g.proposed[c.id] ?? 0,
      feedback: g.feedback[c.id] ?? null,
    })),
  };
}

function instructorAssignment(ctx: MockContext, id: string | undefined): MockAssignment | Response {
  const a = visibleAssignment(ctx, id);
  if (!a) return error(404, "not_found");
  if (ctx.user.role !== "instructor") return error(403, "forbidden");
  return a;
}

export const gradingHandler: MockHandler = (req, ctx) => {
  let p: Record<string, string> | null;

  // MOCK(C4): §10 POST /assignments/{id}/grading-runs
  if ((p = route("POST", "/api/assignments/:id/grading-runs", req))) {
    const a = instructorAssignment(ctx, p.id);
    if (a instanceof Response) return a;
    if (a.status !== "published") return error(400, "invalid_request");
    const run = { id: ctx.world.newId(), assignment_id: a.id, started_at: new Date(ctx.now()).toISOString() };
    ctx.world.runs.push(run);
    // Grade every submission that has no live proposed grade yet.
    const todo = ctx.world.submissions.filter(
      (s) => s.assignment_id === a.id && !ctx.world.proposed.some((g) => g.submission_id === s.id && g.status !== "rejected"),
    );
    todo.forEach((s, i) => ctx.world.proposed.push(gradeSubmission(ctx.world, a, s, i)));
    const body: StartRunResponse = { run_id: run.id, submissions: todo.length };
    return json(201, body);
  }

  // MOCK(C4): §10 GET /assignments/{id}/proposed-grades
  if ((p = route("GET", "/api/assignments/:id/proposed-grades", req))) {
    const a = instructorAssignment(ctx, p.id);
    if (a instanceof Response) return a;
    const rows: ProposedGradeRow[] = ctx.world.proposed
      .filter((g) => g.assignment_id === a.id)
      .map((g) => {
        const s = ctx.world.submissions.find((x) => x.id === g.submission_id);
        const student = MOCK_USERS.find((u) => u.id === s?.student_id);
        return {
          id: g.id,
          submission_id: g.submission_id,
          student: { id: student?.id ?? "", display_name: student?.display_name ?? "Unknown student" },
          total: g.total,
          max_total: g.max_total,
          status: g.status,
          flags: [...g.flags],
        };
      });
    return json(200, rows);
  }

  // MOCK(D3): §10 POST /proposed-grades/approve (re-auth, C28); approving releases (ASSUMED)
  if (route("POST", "/api/proposed-grades/approve", req)) {
    if (ctx.user.role !== "instructor") return error(403, "forbidden");
    if (!ctx.reauthFresh()) return error(401, "reauth_required");
    const ids = isRecord(req.body) ? req.body.proposed_grade_ids : undefined;
    if (!Array.isArray(ids) || ids.length === 0 || !ids.every((x) => typeof x === "string")) return error(400, "invalid_request");
    const grades = ids.map((id) => ctx.world.proposed.find((g) => g.id === id));
    // All or nothing: every ID must be a pending grade in a course this instructor teaches.
    for (const g of grades) {
      if (!g || g.status !== "pending" || !visibleAssignment(ctx, g.assignment_id)) return error(404, "not_found");
    }
    const at = new Date(ctx.now()).toISOString();
    for (const g of grades) {
      g!.status = "released";
      g!.released_at = at;
    }
    const body: ApproveResponse = { released: grades.length };
    return json(200, body);
  }

  return undefined;
};
