/**
 * Appeals, grade-change proposals, drafts, manual queue, audit and course
 * controls (A7). Routes: §10 Grading, Instructor agent, Appeals, Audit and
 * Controls rows (owners C, D, E); docs/plan/C-agent-llm-engineer.md C7.
 * Bodies are ASSUMED and go into the next §10 proposal (A7 worklog).
 */
import type { CriterionKind } from "./content";

export interface PersonRef {
  id: string;
  display_name: string;
}

/** §10 GET /courses/{id}/appeals (instructor). ASSUMED body. */
export interface AppealRow {
  id: string;
  submission_id: string;
  student: PersonRef;
  assignment_title: string;
  status: "open" | "proposed" | "decided";
  created_at: string;
  proposal_id: string | null;
}

export interface ScoreComparison {
  criterion_id: string;
  label: string;
  kind: CriterionKind;
  max_points: number;
  current: number;
  proposed: number;
}

/**
 * GET /grade-change-proposals/{id} (C7 plan; not in §10's table yet).
 * Every number comes from the database, never from the agent's text (C25).
 */
export interface GradeChangeProposal {
  id: string;
  status: "pending" | "accepted" | "rejected";
  appeal: { id: string; reason_text: string; student: PersonRef; created_at: string };
  submission_id: string;
  assignment_title: string;
  criteria: ScoreComparison[];
  current_total: number;
  proposed_total: number;
  max_total: number;
  /** Model-written: SafeMarkdown, labelled as written by the AI assistant. */
  rationale: string;
  decided_by: PersonRef | null;
  decided_at: string | null;
}

/** §10 POST /grade-change-proposals/{id}/decide (re-auth). */
export interface DecideRequest {
  decision: "accept" | "reject";
}

export type DraftKind = "assignment" | "answer_key" | "rubric";

export interface DraftAssignmentPayload {
  title: string;
  instructions: string;
  criteria: { label: string; max_points: number; kind: CriterionKind }[];
}

export interface DraftAnswerKeyPayload {
  assignment_id: string;
  assignment_title: string;
  entries: { criterion_id: string; label: string; content: string; expected: string | null }[];
}

/** §10 GET /drafts/{id}; ASSUMED list route GET /courses/{id}/drafts. */
export interface Draft {
  id: string;
  kind: DraftKind;
  status: "pending" | "accepted" | "rejected";
  created_by_agent: string;
  created_at: string;
  payload: DraftAssignmentPayload | DraftAnswerKeyPayload;
  /** Accepting needs re-auth (keys only, §10). */
  requires_reauth: boolean;
}

/** §10 GET /courses/{id}/manual-queue. ASSUMED body; reason codes from C5/C30. */
export interface ManualQueueItem {
  id: string;
  submission_id: string;
  assignment_id: string;
  assignment_title: string;
  student: PersonRef;
  reason_code: "paused" | "validator_rejected" | "step_limit" | "budget_exceeded" | "grader_error";
  created_at: string;
  resolved_at: string | null;
}

/** §10 POST /manual-queue/{id}/resolve: the instructor's scores, released via D3. */
export interface ResolveRequest {
  scores: Record<string, number>;
}

/** One audit row (01-interfaces.md §8), plus an ASSUMED display label for the actor. */
export interface AuditRow {
  id: string;
  ts: string;
  actor_kind: "agent" | "user" | "system";
  actor_id: string;
  actor_display: string;
  on_behalf_of: string | null;
  course_id: string | null;
  action: string;
  /** Free text replaced by length and hash; numbers and IDs only (§8). */
  args_redacted: Record<string, unknown>;
  decision: "allowed" | "denied";
  reason_code: string | null;
  result_summary: Record<string, unknown>;
  model_id: string | null;
  prompt_version: string | null;
}

export interface AlertRow {
  id: string;
  rule: string;
  severity: "low" | "medium" | "high";
  created_at: string;
  details: Record<string, unknown>;
  acknowledged_by: string | null;
}

/** §10 GET /courses/{id}/audit (instructor). ASSUMED body: rows, chain status (E11 verifier), alerts. */
export interface AuditResponse {
  chain: { status: "intact" | "broken"; rows_checked: number; first_broken_row: string | null };
  alerts: AlertRow[];
  rows: AuditRow[];
}

/** ASSUMED route GET /courses/{id}/controls (§3.1 course_controls); members may read it. */
export interface CourseControls {
  course_id: string;
  agents_paused: boolean;
  paused_by: PersonRef | null;
  paused_at: string | null;
  reason: string | null;
}
