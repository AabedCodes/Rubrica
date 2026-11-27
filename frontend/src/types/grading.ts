/**
 * Grading runs and the review list (A2; routes owned by C for runs, D for
 * approve and release, 01-interfaces.md §10). Bodies are ASSUMED.
 */

/** §7 flags stored on proposed_grades.flags (C36). */
export type GradeFlag =
  | "full_marks"
  | "disagreement"
  | "outlier"
  | "quote_not_found"
  | "citation_not_supported"
  | "feedback_contains_key_text";

export type ProposedGradeStatus = "pending" | "approved" | "released" | "rejected";

/** One row of §10 GET /assignments/{id}/proposed-grades. ASSUMED body. */
export interface ProposedGradeRow {
  id: string;
  submission_id: string;
  student: { id: string; display_name: string };
  total: number;
  max_total: number;
  status: ProposedGradeStatus;
  flags: GradeFlag[];
}

/** §10 POST /assignments/{id}/grading-runs. ASSUMED response. */
export interface StartRunResponse {
  run_id: string;
  submissions: number;
}

/**
 * §10 POST /proposed-grades/approve (re-auth, C28). ASSUMED body. Score changes
 * from the review screen are added in A5. ASSUMED: approving hands the grades
 * to the release service (D3), which publishes them.
 */
export interface ApproveRequest {
  proposed_grade_ids: string[];
  /** A5: optional instructor score changes (see ScoreChanges). */
  score_changes?: ScoreChanges;
}

export interface ApproveResponse {
  released: number;
}

/* ---------------------------------------------------------------- A5 review detail */

/** A quote the grader relied on, and whether code found it verbatim in the text (§7 rule 5). */
export interface QuoteCheck {
  text: string;
  found: boolean;
}

/** Objective criteria are marked by code against the key (C20); shown to instructors only. */
export interface ObjectiveMark {
  answer: string | null;
  expected: string;
  mark: number;
}

export interface CriterionReview {
  criterion_id: string;
  label: string;
  kind: "objective" | "open";
  max_points: number;
  attempt1: number;
  attempt2: number;
  proposed: number;
  /** Model-written: render with SafeMarkdown, labelled as written by the AI grader. */
  feedback: string | null;
  quotes: QuoteCheck[];
  objective: ObjectiveMark | null;
}

/** §3.1 citation_verdicts.verdict. */
export type CitationVerdict = "supports" | "does_not_support" | "unrelated" | "unreadable";

export interface CitationReview {
  url: string;
  claim: string;
  verdict: CitationVerdict;
}

/**
 * ASSUMED route (A5): GET /proposed-grades/{id}, instructors of the course only.
 * §10 has no route for one proposed grade with its attempts, quotes and
 * citations; the review screen (C36) needs all of them. `flags` includes
 * `outlier`, computed by the server when the screen loads (§7).
 */
export interface ProposedGradeDetail extends ProposedGradeRow {
  assignment_id: string;
  assignment_title: string;
  criteria: CriterionReview[];
  citations: CitationReview[];
}

/** §10 GET /submissions/{id}/extracted-text (instructor). ASSUMED body. */
export interface ExtractedText {
  submission_id: string;
  text: string;
}

/**
 * ASSUMED addition to §10 POST /proposed-grades/approve (A5): the instructor's
 * per-criterion changes, keyed by proposed grade ID, then criterion ID. The
 * server checks each against the criterion maximum and audits before and after.
 */
export type ScoreChanges = Record<string, Record<string, number>>;
