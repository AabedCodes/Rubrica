/**
 * A7 mocked routes: appeals and grade-change proposals (MOCK(C7), decided via
 * MOCK(D3)), drafts (MOCK(C7)), manual queue (MOCK(D3)), audit view
 * (MOCK(E11)) and course pause (MOCK(E10)).
 *
 * Every decision that changes a grade or publishes something checks re-auth
 * where §10 marks it, and writes an audit row (R9) with before and after values.
 */
import type {
  AppealRow,
  AuditResponse,
  CourseControls,
  Draft,
  DraftAnswerKeyPayload,
  DraftAssignmentPayload,
  GradeChangeProposal,
  ManualQueueItem,
  PersonRef,
} from "../types/oversight";
import { writeAudit } from "./audit";
import { error, isRecord, json, route, type MockContext, type MockHandler } from "./http";
import { MOCK_USERS, type MockAssignment, type MockControls, type MockProposedGrade, type MockWorld } from "./state";

const isHalfStep = (n: number) => Number.isFinite(n) && (n * 2) % 1 === 0;

function person(id: string | null): PersonRef | null {
  if (!id) return null;
  const u = MOCK_USERS.find((x) => x.id === id);
  return { id, display_name: u?.display_name ?? "Unknown" };
}

function displayActor(id: string): string {
  return MOCK_USERS.find((u) => u.id === id)?.display_name ?? id;
}

function submissionContext(world: MockWorld, submissionId: string) {
  const s = world.submissions.find((x) => x.id === submissionId);
  const a = s && world.assignments.find((x) => x.id === s.assignment_id);
  return s && a ? { s, a } : null;
}

/** Instructor of the course this record belongs to; anyone else gets 404 (§10.1). */
function instructorCourse(ctx: MockContext, courseId: string | undefined): boolean {
  return ctx.user.role === "instructor" && !!courseId && ctx.enrolledIn(courseId);
}

function releasedGrade(world: MockWorld, submissionId: string): MockProposedGrade | undefined {
  return world.proposed.find((g) => g.submission_id === submissionId && g.status === "released");
}

export function controlsFor(world: MockWorld, courseId: string): MockControls {
  return (world.controls[courseId] ??= { agents_paused: false, paused_by: null, paused_at: null, reason: null });
}

function toControls(world: MockWorld, courseId: string): CourseControls {
  const c = controlsFor(world, courseId);
  return { course_id: courseId, agents_paused: c.agents_paused, paused_by: person(c.paused_by), paused_at: c.paused_at, reason: c.reason };
}

function proposalView(ctx: MockContext, id: string | undefined): GradeChangeProposal | null {
  const w = ctx.world;
  const p = w.proposals.find((x) => x.id === id);
  const appeal = p && w.appeals.find((x) => x.id === p.appeal_id);
  const sc = p && submissionContext(w, p.submission_id);
  if (!p || !appeal || !sc || !instructorCourse(ctx, sc.a.course_id)) return null;
  const grade = releasedGrade(w, p.submission_id);
  const criteria = sc.a.criteria.map((c) => ({
    criterion_id: c.id,
    label: c.label,
    kind: c.kind,
    max_points: c.max_points,
    current: grade?.proposed[c.id] ?? 0,
    proposed: p.proposed_scores[c.id] ?? grade?.proposed[c.id] ?? 0,
  }));
  return {
    id: p.id,
    status: p.status,
    appeal: { id: appeal.id, reason_text: appeal.reason_text, student: person(appeal.student_id)!, created_at: appeal.created_at },
    submission_id: p.submission_id,
    assignment_title: sc.a.title,
    criteria,
    current_total: criteria.reduce((s, c) => s + c.current, 0),
    proposed_total: criteria.reduce((s, c) => s + c.proposed, 0),
    max_total: criteria.reduce((s, c) => s + c.max_points, 0),
    rationale: p.rationale,
    decided_by: person(p.decided_by),
    decided_at: p.decided_at,
  };
}

function draftView(ctx: MockContext, id: string | undefined): Draft | null {
  const d = ctx.world.drafts.find((x) => x.id === id);
  if (!d || !instructorCourse(ctx, d.course_id)) return null;
  return {
    id: d.id,
    kind: d.kind,
    status: d.status,
    created_by_agent: d.created_by_agent,
    created_at: d.created_at,
    payload: structuredClone(d.payload),
    requires_reauth: d.kind === "answer_key", // §10: "(re-auth for keys)"
  };
}

function queueView(world: MockWorld, q: MockWorld["manualQueue"][number]): ManualQueueItem | null {
  const sc = submissionContext(world, q.submission_id);
  if (!sc) return null;
  return {
    id: q.id,
    submission_id: q.submission_id,
    assignment_id: sc.a.id,
    assignment_title: sc.a.title,
    student: person(sc.s.student_id)!,
    reason_code: q.reason_code,
    created_at: q.created_at,
    resolved_at: q.resolved_at,
  };
}

/** Scores for every criterion, each 0..max in 0.5 steps (§7); null if anything is off. */
function validScores(a: MockAssignment, raw: unknown, requireAll: boolean): Record<string, number> | null {
  if (!isRecord(raw)) return null;
  const out: Record<string, number> = {};
  for (const c of a.criteria) {
    const v = raw[c.id];
    if (v === undefined && !requireAll) continue;
    if (typeof v !== "number" || v < 0 || v > c.max_points || !isHalfStep(v)) return null;
    out[c.id] = v;
  }
  return Object.keys(raw).every((k) => a.criteria.some((c) => c.id === k)) ? out : null;
}

export const oversightHandler: MockHandler = (req, ctx) => {
  const w = ctx.world;
  let p: Record<string, string> | null;

  // MOCK(C7): §10 GET /courses/{id}/appeals
  if ((p = route("GET", "/api/courses/:id/appeals", req))) {
    if (!instructorCourse(ctx, p.id)) return ctx.enrolledIn(p.id!) ? error(403, "forbidden") : error(404, "not_found");
    const rows: AppealRow[] = w.appeals
      .map((ap) => ({ ap, sc: submissionContext(w, ap.submission_id) }))
      .filter((x) => x.sc?.a.course_id === p!.id)
      .map(({ ap, sc }) => ({
        id: ap.id,
        submission_id: ap.submission_id,
        student: person(ap.student_id)!,
        assignment_title: sc!.a.title,
        status: ap.status,
        created_at: ap.created_at,
        proposal_id: w.proposals.find((x) => x.appeal_id === ap.id)?.id ?? null,
      }));
    return json(200, rows);
  }

  // MOCK(C7): GET /grade-change-proposals/{id} (C7 plan; database values only, C25)
  if ((p = route("GET", "/api/grade-change-proposals/:id", req))) {
    const view = proposalView(ctx, p.id);
    return view ? json(200, view) : error(404, "not_found");
  }

  // MOCK(D3): §10 POST /grade-change-proposals/{id}/decide (re-auth, C28)
  if ((p = route("POST", "/api/grade-change-proposals/:id/decide", req))) {
    const view = proposalView(ctx, p.id);
    if (!view) return error(404, "not_found");
    if (!ctx.reauthFresh()) return error(401, "reauth_required");
    const decision = isRecord(req.body) ? req.body.decision : undefined;
    if (decision !== "accept" && decision !== "reject") return error(400, "invalid_request");
    const proposal = w.proposals.find((x) => x.id === p!.id)!;
    if (proposal.status !== "pending") return error(400, "invalid_request");
    const changes: { criterion_id: string; before: number; after: number }[] = [];
    if (decision === "accept") {
      const grade = releasedGrade(w, proposal.submission_id);
      if (!grade) return error(400, "invalid_request");
      for (const c of view.criteria) {
        if (c.current !== c.proposed) {
          changes.push({ criterion_id: c.criterion_id, before: c.current, after: c.proposed });
          grade.proposed[c.criterion_id] = c.proposed;
        }
      }
      grade.total = Object.values(grade.proposed).reduce((s, n) => s + n, 0);
      grade.changes.push(...changes);
    }
    proposal.status = decision === "accept" ? "accepted" : "rejected";
    proposal.decided_by = ctx.user.id;
    proposal.decided_at = new Date(ctx.now()).toISOString();
    const appeal = w.appeals.find((x) => x.id === proposal.appeal_id);
    if (appeal) appeal.status = "decided";
    writeAudit(ctx, {
      action: "decide_appeal",
      course_id: submissionContext(w, proposal.submission_id)?.a.course_id ?? null,
      args_redacted: { proposal_id: proposal.id, decision, score_changes: changes },
      result_summary: { proposal_status: proposal.status, changed_criteria: changes.length },
    });
    return json(200, proposalView(ctx, p.id));
  }

  // MOCK(C7): ASSUMED route GET /courses/{id}/drafts
  if ((p = route("GET", "/api/courses/:id/drafts", req))) {
    if (!instructorCourse(ctx, p.id)) return ctx.enrolledIn(p.id!) ? error(403, "forbidden") : error(404, "not_found");
    return json(200, w.drafts.filter((d) => d.course_id === p!.id).map((d) => draftView(ctx, d.id)));
  }

  // MOCK(C7): §10 GET /drafts/{id}
  if ((p = route("GET", "/api/drafts/:id", req))) {
    const view = draftView(ctx, p.id);
    return view ? json(200, view) : error(404, "not_found");
  }

  // MOCK(D3): §10 POST /drafts/{id}/accept (re-auth for keys) and ASSUMED POST /drafts/{id}/reject
  if ((p = route("POST", "/api/drafts/:id/accept", req)) || (p = route("POST", "/api/drafts/:id/reject", req))) {
    const accept = req.path.endsWith("/accept");
    const view = draftView(ctx, p.id);
    if (!view) return error(404, "not_found");
    if (view.status !== "pending") return error(400, "invalid_request");
    if (accept && view.requires_reauth && !ctx.reauthFresh()) return error(401, "reauth_required");
    const draft = w.drafts.find((x) => x.id === p!.id)!;
    let result: Record<string, unknown> = {};
    if (accept && draft.kind === "assignment") {
      // Accepting creates a DRAFT assignment the instructor can still edit; nothing is published.
      const pl = draft.payload as DraftAssignmentPayload;
      const a: MockAssignment = {
        id: w.newId(),
        course_id: draft.course_id,
        title: pl.title,
        instructions: pl.instructions,
        status: "draft",
        due_at: new Date(ctx.now() + 14 * 24 * 60 * 60 * 1000).toISOString(),
        version: 1,
        criteria: pl.criteria.map((c, position) => ({ ...c, id: w.newId(), position })),
        answerKey: null,
      };
      w.assignments.push(a);
      result = { assignment_id: a.id };
    } else if (accept && draft.kind === "answer_key") {
      const pl = draft.payload as DraftAnswerKeyPayload;
      const a = w.assignments.find((x) => x.id === pl.assignment_id);
      if (!a) return error(400, "invalid_request");
      a.answerKey = {
        assignment_id: a.id,
        status: "approved",
        version: (a.answerKey?.version ?? 0) + 1,
        entries: pl.entries.map((e) => ({ criterion_id: e.criterion_id, content: e.content, expected: null })),
      };
      result = { assignment_id: a.id, key_version: a.answerKey.version };
    }
    draft.status = accept ? "accepted" : "rejected";
    writeAudit(ctx, {
      action: accept ? "accept_draft" : "reject_draft",
      course_id: draft.course_id,
      args_redacted: { draft_id: draft.id, kind: draft.kind },
      result_summary: result,
    });
    return json(200, draftView(ctx, p.id));
  }

  // MOCK(D3): §10 GET /courses/{id}/manual-queue
  if ((p = route("GET", "/api/courses/:id/manual-queue", req))) {
    if (!instructorCourse(ctx, p.id)) return ctx.enrolledIn(p.id!) ? error(403, "forbidden") : error(404, "not_found");
    const items = w.manualQueue.map((q) => queueView(w, q)).filter((q) => q && submissionContext(w, q.submission_id)?.a.course_id === p!.id);
    return json(200, items);
  }

  // MOCK(D3): §10 POST /manual-queue/{id}/resolve: the instructor's scores, released through D3's record-manual-grade
  if ((p = route("POST", "/api/manual-queue/:id/resolve", req))) {
    const q = w.manualQueue.find((x) => x.id === p!.id);
    const sc = q && submissionContext(w, q.submission_id);
    if (!q || !sc || !instructorCourse(ctx, sc.a.course_id)) return error(404, "not_found");
    if (q.resolved_at) return error(400, "invalid_request");
    const scores = validScores(sc.a, isRecord(req.body) ? req.body.scores : undefined, true);
    if (!scores) return error(400, "invalid_request");
    const at = new Date(ctx.now()).toISOString();
    const total = Object.values(scores).reduce((s, n) => s + n, 0);
    w.proposed.push({
      id: w.newId(),
      assignment_id: sc.a.id,
      submission_id: sc.s.id,
      attempts: [{}, {}],
      proposed: scores,
      feedback: {},
      flags: [],
      total,
      max_total: sc.a.criteria.reduce((s, c) => s + c.max_points, 0),
      status: "released",
      released_at: at,
      quotes: {},
      citations: [],
      changes: [],
    });
    q.resolved_by = ctx.user.id;
    q.resolved_at = at;
    writeAudit(ctx, {
      action: "manual_grade",
      course_id: sc.a.course_id,
      args_redacted: { queue_id: q.id, submission_id: sc.s.id, scores },
      result_summary: { released: 1, total },
    });
    return json(200, queueView(w, q));
  }

  // MOCK(E11): §10 GET /courses/{id}/audit (instructor); chain status from E's verifier
  if ((p = route("GET", "/api/courses/:id/audit", req))) {
    if (!instructorCourse(ctx, p.id)) return ctx.enrolledIn(p.id!) ? error(403, "forbidden") : error(404, "not_found");
    const rows = w.audit
      .filter((r) => r.course_id === p!.id)
      .map((r) => ({ ...r, actor_display: displayActor(r.actor_id) }))
      .sort((a, b) => b.ts.localeCompare(a.ts));
    const body: AuditResponse = {
      chain: { status: "intact", rows_checked: w.audit.length, first_broken_row: null },
      alerts: w.alerts
        .filter((a) => a.course_id === p!.id)
        .map((a) => ({ id: a.id, rule: a.rule, severity: a.severity, created_at: a.created_at, details: a.details, acknowledged_by: a.acknowledged_by })),
      rows,
    };
    return json(200, body);
  }

  // MOCK(E10): ASSUMED route GET /courses/{id}/controls (any course member)
  if ((p = route("GET", "/api/courses/:id/controls", req))) {
    if (!ctx.enrolledIn(p.id!)) return error(404, "not_found");
    return json(200, toControls(w, p.id!));
  }

  // MOCK(E10): §10 POST /courses/{id}/pause and /resume (instructor, re-auth, C30)
  if ((p = route("POST", "/api/courses/:id/pause", req)) || (p = route("POST", "/api/courses/:id/resume", req))) {
    const pause = req.path.endsWith("/pause");
    if (!instructorCourse(ctx, p.id)) return ctx.enrolledIn(p.id!) ? error(403, "forbidden") : error(404, "not_found");
    if (!ctx.reauthFresh()) return error(401, "reauth_required");
    const reason = isRecord(req.body) && typeof req.body.reason === "string" ? req.body.reason.trim() : "";
    if (pause && (!reason || reason.length > 500)) return error(400, "invalid_request");
    const c = controlsFor(w, p.id!);
    Object.assign(
      c,
      pause
        ? { agents_paused: true, paused_by: ctx.user.id, paused_at: new Date(ctx.now()).toISOString(), reason }
        : { agents_paused: false, paused_by: null, paused_at: null, reason: null },
    );
    writeAudit(ctx, {
      action: pause ? "pause" : "resume",
      course_id: p.id!,
      args_redacted: pause ? { reason: { length: reason.length, sha256: "mock" } } : {},
      result_summary: { agents_paused: c.agents_paused },
    });
    return json(200, toControls(w, p.id!));
  }

  return undefined;
};
