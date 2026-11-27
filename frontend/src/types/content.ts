/**
 * Assignments, rubrics, answer keys and submissions (A2; owner of the routes: D, task D6).
 *
 * Columns follow 01-interfaces.md §3.1. §10 names some of these routes but no
 * bodies, and lacks others entirely; every shape and route marked ASSUMED is
 * part of the §10 proposal in the A2 worklog.
 */

export type CriterionKind = "objective" | "open";

/** One rubric row as the instructor edits it (D6: `{label, max_points, kind}`). */
export interface CriterionInput {
  label: string;
  max_points: number;
  kind: CriterionKind;
}

/** §3.1 rubric_criteria. */
export interface Criterion extends CriterionInput {
  id: string;
  position: number;
}

export type AssignmentStatus = "draft" | "published";

/** ASSUMED route: GET /courses/{id}/assignments (students see published only). */
export interface AssignmentSummary {
  id: string;
  course_id: string;
  title: string;
  status: AssignmentStatus;
  due_at: string; // ISO 8601, §3.1 timestamptz
}

/** ASSUMED route: GET /assignments/{id}; also returned by create, rubric and publish. */
export interface Assignment extends AssignmentSummary {
  instructions: string;
  version: number;
  criteria: Criterion[];
}

/** §10 POST /courses/{id}/assignments. ASSUMED body. */
export interface CreateAssignmentRequest {
  title: string;
  instructions: string;
  due_at: string;
}

/** §10 PUT /assignments/{id}/rubric. ASSUMED body (D6 names the row fields). */
export interface PutRubricRequest {
  criteria: CriterionInput[];
}

/** §3.1 answer_keys.expected, objective criteria only. */
export type ExpectedAnswer = { type: "choice"; value: string } | { type: "numeric"; value: number; tolerance: number };

export interface AnswerKeyEntry {
  criterion_id: string;
  content: string;
  expected: ExpectedAnswer | null;
}

/**
 * ASSUMED route: GET /assignments/{id}/answer-key (instructors only, never
 * students, T-01). §10 PUT /assignments/{id}/answer-key stores it as `draft`
 * (D6); there is no route yet for an instructor to accept their own key.
 */
export interface AnswerKey {
  assignment_id: string;
  status: "draft" | "approved";
  version: number;
  entries: AnswerKeyEntry[];
}

export interface PutAnswerKeyRequest {
  entries: AnswerKeyEntry[];
}

/**
 * §10 POST /assignments/{id}/submissions. ASSUMED as multipart/form-data with
 * fields `body_text`, `objective_answers` (JSON object criterion_id → answer)
 * and optional `file` (PDF), because D6 allows an optional PDF.
 */
export const MAX_PDF_BYTES = 10 * 1024 * 1024; // ASSUMED limit; the server enforces its own

/** A student's released score for one criterion. Feedback is model-written: render with SafeMarkdown. */
export interface ReleasedCriterionScore {
  criterion_id: string;
  label: string;
  kind: CriterionKind;
  max_points: number;
  score: number;
  feedback: string | null;
}

export interface ReleasedGrade {
  total: number;
  max_total: number;
  released_at: string;
  criteria: ReleasedCriterionScore[];
}

/**
 * §10 GET /assignments/{id}/my-submission. ASSUMED body; `grade` is present
 * only once the grade is released (R10). 404 when nothing was submitted.
 */
export interface MySubmission {
  id: string;
  submitted_at: string;
  body_text: string;
  objective_answers: Record<string, string>;
  file_name: string | null;
  grade: ReleasedGrade | null;
}
